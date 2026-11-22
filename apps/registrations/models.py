from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from . import utils

RESERVED_KEYS = {"full_name", "email", "phone", "caspam_roll", "participant_type", "second_factor",
                 "payment_method", "payment_reference", "website", "csrfmiddlewaretoken"}


class StudentDataset(models.Model):
    """An authorized list of CASPAM students, uploaded by an administrator (Excel/CSV).
    The uploaded file itself is NOT kept; only normalised rows are stored, with CNIC and
    mobile numbers kept as keyed hashes (never readable)."""
    name = models.CharField(max_length=150, help_text="e.g. 'CASPAM students — Fall 2026 (TEST DATA)'")
    notes = models.CharField(max_length=300, blank=True)
    is_test_data = models.BooleanField("Fictional / test data", default=False)
    is_active = models.BooleanField(default=True)
    row_count = models.PositiveIntegerField(default=0, editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "CASPAM student dataset"
        permissions = [("upload_dataset", "Can upload / replace CASPAM student datasets")]

    def __str__(self):
        return self.name


class AuthorizedStudent(models.Model):
    dataset = models.ForeignKey(StudentDataset, on_delete=models.CASCADE, related_name="students")
    roll_norm = models.CharField(max_length=40, db_index=True)
    roll_display = models.CharField(max_length=40)
    name = models.CharField(max_length=150)
    cnic_hash = models.CharField(max_length=64, blank=True)
    cnic_last4 = models.CharField(max_length=4, blank=True)
    phone_hash = models.CharField(max_length=64, blank=True)
    phone_last4 = models.CharField(max_length=4, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dataset", "roll_norm"], name="uniq_roll_per_dataset")]
        ordering = ["roll_norm"]

    def __str__(self):
        return f"{self.roll_display} · {utils.mask_name(self.name)}"


class EventRegistrationConfig(models.Model):
    SF_NONE, SF_MOBILE, SF_CNIC = "none", "mobile", "cnic"
    SECOND_FACTOR = [(SF_NONE, "None (roll number + name only)"),
                     (SF_MOBILE, "WhatsApp/mobile number (recommended)"),
                     (SF_CNIC, "CNIC — only if genuinely required and authorised")]
    PH_REQ, PH_OPT, PH_HIDE = "required", "optional", "hidden"
    PHONE_MODE = [(PH_REQ, "Required"), (PH_OPT, "Optional"), (PH_HIDE, "Do not ask")]

    event = models.OneToOneField("events.Event", on_delete=models.CASCADE, related_name="reg_config")
    builtin_enabled = models.BooleanField(
        "Use the built-in registration system for this event", default=False,
        help_text="OFF = the event keeps its old registration box/link exactly as before.")
    # --- CASPAM verification: independent per event ---
    caspam_verification_enabled = models.BooleanField(
        "Enable CASPAM Student Verification and Special Ticket Pricing", default=False,
        help_text="ON: participants who claim to be CASPAM students must be verified against the dataset below "
                  "and the CASPAM / external prices apply. OFF: no CASPAM question, no dataset matching, no CASPAM pricing.")
    dataset = models.ForeignKey(StudentDataset, null=True, blank=True, on_delete=models.SET_NULL, related_name="configs",
                                verbose_name="Authorised student dataset")
    second_factor = models.CharField("Second identifier used for matching", max_length=8, choices=SECOND_FACTOR, default=SF_MOBILE)
    # --- pricing (PKR). The server always computes the amount from these. ---
    caspam_price = models.DecimalField("Verified CASPAM student price (PKR)", max_digits=9, decimal_places=2, default=Decimal("1500"))
    external_price = models.DecimalField("External participant price (PKR)", max_digits=9, decimal_places=2, default=Decimal("2000"))
    standard_price = models.DecimalField("Ticket price when CASPAM verification is OFF (PKR, 0 = free)", max_digits=9, decimal_places=2, default=Decimal("0"))
    # --- rules ---
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Leave empty for no limit.")
    phone_mode = models.CharField("Contact number", max_length=8, choices=PHONE_MODE, default=PH_REQ)
    pass_required = models.BooleanField("Issue a live digital entry pass", default=True)
    confirmation_note = models.TextField("Message shown after registering", blank=True)
    payment_instructions = models.TextField("General payment instructions", blank=True,
                                            help_text="Shown with the payment methods below.")

    class Meta:
        verbose_name = "Registration settings"
        verbose_name_plural = "Registration settings (per event)"
        permissions = [("verify_student", "Can resolve student-verification reviews"),
                       ("export_registrations", "Can export registration reports")]

    def __str__(self):
        return f"Registration settings — {self.event}"

    def clean(self):
        if self.caspam_verification_enabled and self.builtin_enabled and not self.dataset_id:
            raise ValidationError({"dataset": "Choose an authorised dataset (or upload one) before turning CASPAM verification on."})
        if self.caspam_verification_enabled and (self.dataset_id and not self.dataset.is_active):
            raise ValidationError({"dataset": "That dataset is switched off."})

    @property
    def uses_caspam(self):
        return self.caspam_verification_enabled

    def active_count(self):
        return self.event.registrations.exclude(state=Registration.CANCELLED).count()

    @property
    def is_full(self):
        return bool(self.capacity) and self.active_count() >= self.capacity

    @property
    def seats_left(self):
        return None if not self.capacity else max(self.capacity - self.active_count(), 0)

    def price_for(self, category):
        """The ONLY place a ticket price is decided."""
        if not self.caspam_verification_enabled:
            return self.standard_price
        return self.caspam_price if category == Registration.CAT_CASPAM else self.external_price


class RegistrationField(models.Model):
    TEXT, LONG, NUMBER, CHOICE, CHECK, EMAIL, TEL = "text", "long", "number", "choice", "checkbox", "email", "tel"
    TYPES = [(TEXT, "Short text"), (LONG, "Long text"), (NUMBER, "Number"), (CHOICE, "Drop-down choice"),
             (CHECK, "Tick box (yes/no)"), (EMAIL, "Email"), (TEL, "Phone number")]
    config = models.ForeignKey(EventRegistrationConfig, on_delete=models.CASCADE, related_name="fields")
    key = models.SlugField(max_length=40, help_text="Internal name, e.g. department (letters, numbers, - or _).")
    label = models.CharField(max_length=160)
    field_type = models.CharField(max_length=10, choices=TYPES, default=TEXT)
    required = models.BooleanField(default=False)
    choices = models.TextField(blank=True, help_text="For drop-down choices: one option per line.")
    help_text = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["config", "key"], name="uniq_field_key_per_event")]

    def __str__(self):
        return self.label

    def clean(self):
        k = (self.key or "").replace("-", "_")
        if k in RESERVED_KEYS or "cnic" in k.lower():
            raise ValidationError({"key": "This name is reserved. CNIC is never collected as an ordinary field "
                                          "(use the verification 'second identifier' setting instead)."})
        if self.field_type == self.CHOICE and not self.choice_list:
            raise ValidationError({"choices": "Add at least one option."})

    @property
    def choice_list(self):
        return [c.strip() for c in self.choices.splitlines() if c.strip()]


class PaymentMethod(models.Model):
    BANK, EASYPAISA, JAZZCASH, CASH, OTHER = "bank", "easypaisa", "jazzcash", "cash", "other"
    KINDS = [(BANK, "Bank transfer"), (EASYPAISA, "Easypaisa"), (JAZZCASH, "JazzCash"),
             (CASH, "Cash (paid to organisers)"), (OTHER, "Other manual method")]
    config = models.ForeignKey(EventRegistrationConfig, on_delete=models.CASCADE, related_name="payment_methods")
    kind = models.CharField(max_length=12, choices=KINDS, default=BANK)
    title = models.CharField(max_length=100, help_text="Shown to participants, e.g. 'Easypaisa'")
    account_title = models.CharField("Account holder", max_length=120, blank=True)
    account_number = models.CharField("Account / mobile number", max_length=60, blank=True)
    instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Registration(models.Model):
    ACTIVE, CANCELLED = "active", "cancelled"
    CAT_CASPAM, CAT_EXTERNAL, CAT_GENERAL = "caspam", "external", "general"
    CATEGORIES = [(CAT_CASPAM, "Verified CASPAM student"), (CAT_EXTERNAL, "External participant"), (CAT_GENERAL, "General participant")]
    V_NOT_REQUIRED, V_VERIFIED, V_REVIEW, V_NOT_VERIFIED = "not_required", "verified", "pending_review", "not_verified"
    VERIFICATION = [(V_NOT_REQUIRED, "Not required"), (V_VERIFIED, "Verified"),
                    (V_REVIEW, "Pending manual review"), (V_NOT_VERIFIED, "Not verified")]
    UNPAID, SUBMITTED, REVIEW, PAID, REJECTED, REFUNDED, NOT_REQUIRED = (
        "unpaid", "payment_submitted", "under_review", "paid", "rejected", "refunded", "not_required")
    PAYMENT = [(UNPAID, "Unpaid"), (SUBMITTED, "Payment Submitted"), (REVIEW, "Under Review"), (PAID, "Paid"),
               (REJECTED, "Rejected"), (REFUNDED, "Refunded"), (NOT_REQUIRED, "Free — no payment needed")]
    PAY_TRANSITIONS = {
        UNPAID: {SUBMITTED, PAID},              # PAID directly = cash collected by finance
        SUBMITTED: {REVIEW, PAID, REJECTED},
        REVIEW: {PAID, REJECTED},
        REJECTED: {SUBMITTED, PAID},
        PAID: {REFUNDED},
        REFUNDED: set(), NOT_REQUIRED: set(),
    }

    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="registrations")
    reference = models.CharField(max_length=14, unique=True, default=utils.new_reference, editable=False)
    verification_code = models.CharField(max_length=11, unique=True, default=utils.new_verification_code, editable=False)
    access_token = models.CharField(max_length=64, unique=True, default=utils.new_access_token, editable=False)
    state = models.CharField(max_length=10, default=ACTIVE, choices=[(ACTIVE, "Active"), (CANCELLED, "Cancelled")])
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    answers = models.JSONField(default=dict, blank=True)
    # category & verification
    claimed_caspam = models.BooleanField(default=False)
    category = models.CharField(max_length=10, choices=CATEGORIES, default=CAT_GENERAL)
    caspam_roll = models.CharField("Roll number claimed", max_length=40, blank=True)
    identifier_last4 = models.CharField(max_length=4, blank=True)
    verification_status = models.CharField(max_length=14, choices=VERIFICATION, default=V_NOT_REQUIRED)
    verification_note = models.CharField(max_length=300, blank=True)
    matched_student = models.ForeignKey(AuthorizedStudent, null=True, blank=True, on_delete=models.SET_NULL)
    verification_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    # money
    price = models.DecimalField("Ticket price (PKR)", max_digits=9, decimal_places=2, default=Decimal("0"))
    payment_status = models.CharField(max_length=18, choices=PAYMENT, default=UNPAID)
    payment_method = models.ForeignKey(PaymentMethod, null=True, blank=True, on_delete=models.SET_NULL)
    payment_reference = models.CharField("Transaction / receipt reference", max_length=80, blank=True)
    payment_note = models.CharField(max_length=300, blank=True)
    payment_submitted_at = models.DateTimeField(null=True, blank=True)
    payment_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    payment_reviewed_at = models.DateTimeField(null=True, blank=True)
    # pass & entry
    pass_revoked = models.BooleanField(default=False)
    pass_revoked_reason = models.CharField(max_length=200, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "email"], condition=~Q(state="cancelled"), name="uniq_active_email_per_event"),
            models.UniqueConstraint(fields=["event", "caspam_roll"], condition=~Q(state="cancelled") & ~Q(caspam_roll=""),
                                    name="uniq_active_roll_per_event"),
        ]
        permissions = [("approve_payment", "Can approve / reject / refund payments"),
                       ("manage_pass", "Can activate or revoke entry passes"),
                       ("perform_checkin", "Can use the check-in screen"),
                       ("view_dashboard", "Can see the event registration dashboard")]

    def __str__(self):
        return f"{self.reference} · {self.full_name}"

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    # ---- pass logic (single source of truth) ----
    def pass_blockers(self):
        out = []
        if self.state == self.CANCELLED:
            out.append("This registration was cancelled.")
        if self.verification_status == self.V_REVIEW:
            out.append("Your CASPAM student details are being reviewed by the organisers.")
        if self.payment_status not in (self.PAID, self.NOT_REQUIRED):
            out.append({self.REJECTED: "Your payment was not accepted. Please submit it again.",
                        self.REFUNDED: "Your payment was refunded."}.get(self.payment_status, "Payment has not been confirmed yet."))
        return out

    @property
    def pass_status(self):
        if self.pass_revoked:
            return "revoked"
        if self.checked_in_at:
            return "used"
        return "active" if not self.pass_blockers() else "inactive"

    @property
    def is_checked_in(self):
        return bool(self.checked_in_at)

    @property
    def payment_instructions_visible(self):
        return (self.state == self.ACTIVE and self.price > 0 and self.verification_status != self.V_REVIEW
                and self.payment_status in (self.UNPAID, self.REJECTED))

    def set_payment_status(self, new, user=None, note=""):
        """Validated state machine. Raises ValueError for an illegal jump."""
        if new not in self.PAY_TRANSITIONS.get(self.payment_status, set()):
            raise ValueError(f"Cannot change payment from '{self.get_payment_status_display()}' to '{dict(self.PAYMENT)[new]}'.")
        if new == self.PAID and self.verification_status == self.V_REVIEW:
            raise ValueError("Resolve the student-verification review before approving payment (the price is not final yet).")
        self.payment_status = new
        if user is not None:
            self.payment_reviewed_by, self.payment_reviewed_at = user, timezone.now()
        if note:
            self.payment_note = note[:300]
        self.save()


class AuditLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.SET_NULL)
    registration = models.ForeignKey(Registration, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=60)
    detail = models.CharField(max_length=400, blank=True)
    ip = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit log entry"
        verbose_name_plural = "Audit log"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"

    @classmethod
    def record(cls, action, request=None, user=None, registration=None, event=None, detail=""):
        from apps.core.utils import client_ip
        u = user or (request.user if request is not None and getattr(request, "user", None) and request.user.is_authenticated else None)
        return cls.objects.create(
            user=u, registration=registration, event=event or (registration.event if registration else None),
            action=action, detail=detail[:400], ip=client_ip(request) if request is not None else "")
