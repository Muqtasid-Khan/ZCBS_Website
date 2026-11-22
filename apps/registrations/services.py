"""All business rules live here (verification, pricing, registration, payments, check-in).
Views, admin and tests call these functions; nothing trusts values sent by the browser."""
import csv
import io
import re
import zipfile

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import utils
from .models import AuditLog, AuthorizedStudent, EventRegistrationConfig, Registration, StudentDataset

MAX_DATASET_BYTES = 5 * 1024 * 1024
MAX_DATASET_ROWS = 20000


class RegistrationError(Exception):
    """Message is safe to show to the participant."""


# ------------------------------------------------------------------ verification
def verify_caspam(config, roll, name, second_value=""):
    """Returns (status, student_or_None, internal_note). Never verifies on name alone:
    the roll number must exist in the dataset AND the name AND the second identifier (if configured) must agree."""
    ds = config.dataset
    if not ds or not ds.is_active:
        return Registration.V_REVIEW, None, "No active authorised dataset is attached to this event."
    roll_norm = utils.normalize_roll(roll)
    if not roll_norm:
        return Registration.V_NOT_VERIFIED, None, "No roll number entered."
    student = ds.students.filter(roll_norm=roll_norm).first()
    if student is None:
        return Registration.V_NOT_VERIFIED, None, f"Roll number '{roll_norm}' not found in dataset."
    problems = []
    if not utils.names_match(name, student.name):
        problems.append("name differs from dataset")
    sf = config.second_factor
    if sf == config.SF_MOBILE:
        given = utils.normalize_phone(second_value)
        if not student.phone_hash:
            problems.append("dataset has no mobile number to compare")
        elif not given or utils.secret_hash("phone", given) != student.phone_hash:
            problems.append("mobile number differs from dataset")
    elif sf == config.SF_CNIC:
        given = utils.digits(second_value)
        if not student.cnic_hash:
            problems.append("dataset has no CNIC to compare")
        elif not given or utils.secret_hash("cnic", given) != student.cnic_hash:
            problems.append("CNIC differs from dataset")
    if problems:
        return Registration.V_REVIEW, student, "Conflicting details: " + "; ".join(problems) + "."
    return Registration.V_VERIFIED, student, "Roll number, name and second identifier all match."


def resolve_verification(reg, approve, user, request=None, note=""):
    """Manual review decision (permission checked by the caller)."""
    if reg.verification_status != Registration.V_REVIEW:
        raise ValueError("This registration is not waiting for verification review.")
    with transaction.atomic():
        cfg = reg.event.reg_config
        if approve:
            reg.verification_status, reg.category = Registration.V_VERIFIED, Registration.CAT_CASPAM
        else:
            reg.verification_status, reg.category = Registration.V_NOT_VERIFIED, Registration.CAT_EXTERNAL
            reg.matched_student, reg.caspam_roll = None, ""
        reg.price = cfg.price_for(reg.category)
        if reg.price == 0 and reg.payment_status == Registration.UNPAID:
            reg.payment_status = Registration.NOT_REQUIRED
        reg.verification_reviewed_by = user
        reg.verification_note = (note or reg.verification_note)[:300]
        reg.save()
        AuditLog.record("verification_approved" if approve else "verification_rejected", request, user, reg,
                        detail=f"price now PKR {reg.price}")


# ------------------------------------------------------------------ registration
def can_register(event):
    cfg = getattr(event, "reg_config", None)
    return bool(cfg and cfg.builtin_enabled and event.registration_is_open and event.is_visible)


def create_registration(event, data, request=None):
    """`data` is the validated form data. Raises RegistrationError with a friendly message."""
    cfg = event.reg_config
    if not can_register(event):
        raise RegistrationError("Registration for this event is closed.")
    answers = {}
    for f in cfg.fields.filter(is_active=True):
        v = data.get(f"f_{f.key}")
        if v not in (None, ""):
            answers[f.key] = {"label": f.label, "value": "Yes" if v is True else str(v)}
    claimed = cfg.uses_caspam and data.get("participant_type") == "caspam"
    category, ver, student, note, roll = Registration.CAT_GENERAL, Registration.V_NOT_REQUIRED, None, "", ""
    ident4 = ""
    if cfg.uses_caspam:
        if claimed:
            ver, student, note = verify_caspam(cfg, data.get("caspam_roll", ""), data["full_name"], data.get("second_factor", ""))
            category = Registration.CAT_CASPAM if ver == Registration.V_VERIFIED else Registration.CAT_EXTERNAL
            roll = student.roll_norm if student else ""
            if not student:
                note = (note + f" (entered: {utils.normalize_roll(data.get('caspam_roll', ''))[:20]})")[:300]
            sf = re.sub(r"\D", "", data.get("second_factor", ""))
            ident4 = sf[-4:] if cfg.second_factor != cfg.SF_NONE else ""
        else:
            category = Registration.CAT_EXTERNAL
    price = cfg.price_for(category)       # decided here, on the server — never taken from the form
    method = None
    try:
        with transaction.atomic():
            locked = EventRegistrationConfig.objects.select_for_update().get(pk=cfg.pk)   # serialises capacity checks
            if locked.is_full:
                raise RegistrationError("Sorry, this event has reached its capacity.")
            reg = Registration.objects.create(
                event=event, full_name=data["full_name"].strip(), email=data["email"], phone=data.get("phone", ""),
                answers=answers, claimed_caspam=claimed, category=category, caspam_roll=roll,
                identifier_last4=ident4, verification_status=ver, verification_note=note,
                matched_student=student, price=price,
                payment_status=Registration.NOT_REQUIRED if price == 0 else Registration.UNPAID)
    except IntegrityError:
        raise RegistrationError("This email address or CASPAM roll number is already registered for this event. "
                                "Use 'Find my registration' to open it, or contact the organisers.")
    AuditLog.record("registered", request, None, reg, detail=f"{reg.get_category_display()} / {reg.get_verification_status_display()} / PKR {reg.price}")
    return reg


def submit_payment(reg, method, reference, note="", request=None):
    if reg.state != Registration.ACTIVE or reg.verification_status == Registration.V_REVIEW:
        raise RegistrationError("Payment cannot be submitted yet. The organisers are still checking your details.")
    if reg.payment_status not in (Registration.UNPAID, Registration.REJECTED) or reg.price <= 0:
        raise RegistrationError("No payment is due for this registration.")
    if method is None or method.config_id != reg.event.reg_config.pk or not method.is_active:
        raise RegistrationError("Please choose one of the listed payment methods.")
    reg.payment_method, reg.payment_reference = method, reference.strip()[:80]
    reg.payment_note, reg.payment_submitted_at = note.strip()[:300], timezone.now()
    reg.set_payment_status(Registration.SUBMITTED)
    AuditLog.record("payment_submitted", request, None, reg, detail=f"{method.title} ref {reg.payment_reference}")


def change_payment(reg, new, user, request=None, note=""):
    old = reg.get_payment_status_display()
    reg.set_payment_status(new, user, note)
    AuditLog.record("payment_" + new, request, user, reg, detail=f"{old} → {reg.get_payment_status_display()}")


def set_pass_revoked(reg, revoked, user, request=None, reason=""):
    reg.pass_revoked, reg.pass_revoked_reason = revoked, (reason if revoked else "")[:200]
    reg.save(update_fields=["pass_revoked", "pass_revoked_reason", "updated_at"])
    AuditLog.record("pass_revoked" if revoked else "pass_restored", request, user, reg, detail=reason)


# ------------------------------------------------------------------ check-in
def inspect_code(code, event=None):
    """Read-only look-up used before admitting someone. Returns (reg|None, list of (ok, text))."""
    reg = Registration.objects.select_related("event").filter(verification_code=utils.format_code(code)).first()
    if not reg:
        return None, [(False, "No registration has this code.")]
    checks = [(True, "Registration found.")]
    if event and reg.event_id != event.pk:
        checks.append((False, f"This code belongs to a different event ({reg.event.title})."))
    checks.append((reg.state == Registration.ACTIVE, "Registration is active." if reg.state == Registration.ACTIVE else "Registration was cancelled."))
    paid = reg.payment_status in (Registration.PAID, Registration.NOT_REQUIRED)
    checks.append((paid, "Payment confirmed." if paid else f"Payment not confirmed ({reg.get_payment_status_display()})."))
    elig = reg.verification_status != Registration.V_REVIEW
    checks.append((elig, "Eligibility confirmed." if elig else "Eligibility still under review."))
    checks.append((not reg.pass_revoked, "Pass is active." if not reg.pass_revoked else "Pass was revoked by an administrator."))
    checks.append((not reg.checked_in_at, "Not yet entered." if not reg.checked_in_at
                   else f"ALREADY USED — entered at {timezone.localtime(reg.checked_in_at):%d %b %Y, %H:%M}."))
    return reg, checks


def check_in(code, user, event=None, request=None):
    """Atomic one-time admission. A single conditional UPDATE decides the winner, so two
    simultaneous scans of the same code can never both succeed. Returns (ok, message, reg)."""
    reg, _ = inspect_code(code, event)
    if not reg:
        AuditLog.record("checkin_denied", request, user, detail="unknown code")
        return False, "No registration has this code.", None
    qs = Registration.objects.filter(
        pk=reg.pk, state=Registration.ACTIVE, pass_revoked=False, checked_in_at__isnull=True,
        payment_status__in=[Registration.PAID, Registration.NOT_REQUIRED]).exclude(verification_status=Registration.V_REVIEW)
    if event:
        qs = qs.filter(event=event)
    updated = qs.update(checked_in_at=timezone.now(), checked_in_by=user)
    reg.refresh_from_db()
    if updated == 1:
        AuditLog.record("checkin_ok", request, user, reg)
        return True, "Entry confirmed. The pass is now marked as used.", reg
    _, checks = inspect_code(code, event)
    why = next((t for ok, t in checks if not ok), "Entry not allowed.")
    AuditLog.record("checkin_denied", request, user, reg, detail=why)
    return False, why, reg


# ------------------------------------------------------------------ dataset import
HEADERS = {
    "roll": {"roll", "rollno", "rollnumber", "rollnum", "regno", "registrationnumber", "registrationno", "studentid"},
    "name": {"name", "studentname", "fullname"},
    "cnic": {"cnic", "nic", "cnicnumber", "cnicno"},
    "phone": {"whatsapp", "whatsappnumber", "mobile", "mobilenumber", "phone", "phonenumber", "contact", "contactnumber", "whatsappmobile"},
}


def _key(h):
    return re.sub(r"[^a-z0-9]", "", str(h or "").lower())


def read_table(uploaded):
    """Return list of rows (lists of strings) from a CSV or XLSX upload. Validates type and size."""
    name = (uploaded.name or "").lower()
    if uploaded.size > MAX_DATASET_BYTES:
        raise ValueError("File is larger than 5 MB.")
    raw = uploaded.read()
    if name.endswith(".csv"):
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        return [[c.strip() for c in r] for r in csv.reader(io.StringIO(text))]
    if name.endswith(".xlsx"):
        if not zipfile.is_zipfile(io.BytesIO(raw)):
            raise ValueError("This is not a valid .xlsx file.")
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        return [["" if c is None else str(c).strip() for c in row] for row in ws.iter_rows(values_only=True)]
    raise ValueError("Upload a .csv or .xlsx file.")


def check_upload(uploaded):
    """Validate a file before saving anything. Returns the number of data rows, or raises ValueError."""
    rows = read_table(uploaded)
    uploaded.seek(0)
    if len(rows) < 2:
        raise ValueError("The file has no data rows.")
    header = {_key(h) for h in rows[0]}
    for field in ("roll", "name"):
        if not header & HEADERS[field]:
            raise ValueError("The first row must have headings including a roll number column and a name column.")
    return len(rows) - 1


def import_dataset(dataset, uploaded, replace=True):
    """Parses the file in memory and stores only normalised/hashed rows. The file itself is not saved.
    Returns a dict of counts. Raises ValueError for unusable files."""
    rows = read_table(uploaded)
    if len(rows) < 2:
        raise ValueError("The file has no data rows.")
    if len(rows) - 1 > MAX_DATASET_ROWS:
        raise ValueError(f"Too many rows (limit {MAX_DATASET_ROWS}).")
    header = [_key(h) for h in rows[0]]
    idx = {}
    for field, aliases in HEADERS.items():
        for i, h in enumerate(header):
            if h in aliases and field not in idx:
                idx[field] = i
    if "roll" not in idx or "name" not in idx:
        raise ValueError("The first row must have headings including a roll number column and a name column.")
    seen, objs, skipped, dupes = set(), [], 0, 0
    for r in rows[1:]:
        get = lambda f: (r[idx[f]] if f in idx and idx[f] < len(r) else "").strip()
        roll, name = get("roll"), get("name")
        rn = utils.normalize_roll(roll)
        if not rn or not name:
            skipped += 1
            continue
        if rn in seen:
            dupes += 1
            continue
        seen.add(rn)
        cn, ph = utils.digits(get("cnic")), utils.normalize_phone(get("phone"))
        objs.append(AuthorizedStudent(
            dataset=dataset, roll_norm=rn, roll_display=roll[:40], name=name[:150],
            cnic_hash=utils.secret_hash("cnic", cn) if len(cn) == 13 else "", cnic_last4=cn[-4:] if len(cn) == 13 else "",
            phone_hash=utils.secret_hash("phone", ph) if len(ph) >= 10 else "", phone_last4=ph[-4:] if len(ph) >= 10 else ""))
    if not objs:
        raise ValueError("No usable rows found.")
    with transaction.atomic():
        if replace:
            dataset.students.all().delete()
        AuthorizedStudent.objects.bulk_create(objs, batch_size=500)
        dataset.row_count = dataset.students.count()
        dataset.save(update_fields=["row_count"])
    return {"imported": len(objs), "skipped": skipped, "duplicates": dupes,
            "has_phone": "phone" in idx, "has_cnic": "cnic" in idx}
