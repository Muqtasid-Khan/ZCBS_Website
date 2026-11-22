import io
from datetime import datetime

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import Registration

KINDS = {
    "all": ("All registrations", lambda q: q),
    "caspam": ("Verified CASPAM students", lambda q: q.filter(verification_status=Registration.V_VERIFIED, category=Registration.CAT_CASPAM)),
    "external": ("External participants", lambda q: q.filter(category=Registration.CAT_EXTERNAL)),
    "paid": ("Paid registrations", lambda q: q.filter(payment_status__in=[Registration.PAID, Registration.NOT_REQUIRED])),
    "pending": ("Pending registrations", lambda q: q.exclude(state=Registration.CANCELLED).exclude(
        payment_status__in=[Registration.PAID, Registration.NOT_REQUIRED]) | q.filter(verification_status=Registration.V_REVIEW)),
    "checked_in": ("Checked-in participants", lambda q: q.filter(checked_in_at__isnull=False)),
}
FILLS = {
    "paid": "C6EFCE", "not_required": "C6EFCE", "verified": "C6EFCE", "active": "C6EFCE",
    "unpaid": "FFEB9C", "payment_submitted": "FFEB9C", "under_review": "FFEB9C", "pending_review": "FFEB9C",
    "rejected": "FFC7CE", "refunded": "FFC7CE", "not_verified": "FFC7CE", "revoked": "FFC7CE", "cancelled": "FFC7CE",
}


def _clean(v):
    """Neutralise spreadsheet formula injection from participant-entered text."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def build_workbook(event, kind):
    title, flt = KINDS[kind]
    qs = flt(event.registrations.select_related("payment_method", "checked_in_by").order_by("created_at")).distinct()
    cfg = event.reg_config
    extra = [f.label for f in cfg.fields.filter(is_active=True)]
    cols = ["Reference", "Full name", "Email", "Phone", "Category", "Verification", "Ticket price (PKR)", "Payment status",
            "Payment method", "Payment reference", "Pass status", "Checked in", "Checked in at", "Registered at"]
    if cfg.uses_caspam:
        cols.insert(5, "Roll number (matched)")
    cols += extra
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append([f"{event.title} — {title}"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Exported {timezone.localtime():%d %b %Y %H:%M} · CASPAM verification {'ON' if cfg.uses_caspam else 'OFF'} · CNIC numbers are never stored or exported"])
    ws.append([])
    ws.append(cols)
    head_row = 4
    for c in range(1, len(cols) + 1):
        cell = ws.cell(row=head_row, column=c)
        cell.font, cell.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="14213D")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    status_cols = {}
    for reg in qs:
        row = [reg.reference, reg.full_name, reg.email, reg.phone, reg.get_category_display(), reg.get_verification_status_display(),
               float(reg.price), reg.get_payment_status_display(), reg.payment_method.title if reg.payment_method else "",
               reg.payment_reference, reg.pass_status.title(), "Yes" if reg.checked_in_at else "No",
               timezone.localtime(reg.checked_in_at).replace(tzinfo=None) if reg.checked_in_at else "",
               timezone.localtime(reg.created_at).replace(tzinfo=None)]
        if cfg.uses_caspam:
            row.insert(5, reg.caspam_roll)
        row += [(reg.answers.get(f.key) or {}).get("value", "") for f in cfg.fields.filter(is_active=True)]
        ws.append([_clean(v) for v in row])
        r = ws.max_row
        off = 1 if cfg.uses_caspam else 0
        for col_idx, val in ((6 + off, reg.verification_status), (8 + off, reg.payment_status), (11 + off, reg.pass_status)):
            fill = FILLS.get(val)
            if fill:
                ws.cell(row=r, column=col_idx).fill = PatternFill("solid", fgColor=fill)
        ws.cell(row=r, column=7 + off).number_format = '#,##0'
        for col_idx in (13 + off, 14 + off):
            ws.cell(row=r, column=col_idx).number_format = "dd mmm yyyy hh:mm"
    last = max(ws.max_row, head_row + 1)
    ws.freeze_panes = ws.cell(row=head_row + 1, column=3)
    ws.auto_filter.ref = f"A{head_row}:{get_column_letter(len(cols))}{last}"
    for i, name in enumerate(cols, 1):
        longest = max([len(str(name))] + [len(str(ws.cell(row=r, column=i).value or "")) for r in range(head_row + 1, min(last, 400) + 1)])
        ws.column_dimensions[get_column_letter(i)].width = min(max(longest + 3, 12), 42)
    ws.row_dimensions[head_row].height = 30
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), qs.count()


def filename(event, kind):
    return f"{event.slug[:40]}-{kind}-{datetime.now():%Y%m%d}.xlsx"
