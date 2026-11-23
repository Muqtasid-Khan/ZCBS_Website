from django import forms
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from . import services, utils
from .models import (AuditLog, AuthorizedStudent, EventRegistrationConfig, PaymentMethod, Registration,
                     RegistrationField, StudentDataset)


# ---------------------------------------------------------------- datasets
class DatasetForm(forms.ModelForm):
    upload = forms.FileField(
        required=False, label="Excel (.xlsx) or CSV file",
        help_text="First row = headings. Needed: roll number and name. Optional: CNIC, WhatsApp/mobile. "
                  "The file itself is NOT kept — only roll numbers and names are stored; CNIC and mobile numbers are stored as unreadable hashes. "
                  "Uploading again on an existing dataset REPLACES its rows.")

    class Meta:
        model = StudentDataset
        fields = ["name", "notes", "is_test_data", "is_active"]

    def clean_upload(self):
        f = self.cleaned_data.get("upload")
        if not f and not self.instance.pk:
            raise forms.ValidationError("Please choose a file.")
        if f:
            try:
                services.check_upload(f)
            except ValueError as exc:
                raise forms.ValidationError(str(exc))
        return f


@admin.register(StudentDataset)
class StudentDatasetAdmin(admin.ModelAdmin):
    form = DatasetForm
    list_display = ["name", "row_count", "is_test_data", "is_active", "uploaded_at", "uploaded_by"]
    readonly_fields = ["row_count", "uploaded_by", "uploaded_at"]

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
        f = form.cleaned_data.get("upload")
        if f:
            res = services.import_dataset(obj, f)
            AuditLog.record("dataset_uploaded", request, detail=f"{obj.name}: {res['imported']} rows")
            messages.success(request, f"{res['imported']} students imported ({res['skipped']} skipped, {res['duplicates']} duplicate rolls ignored)."
                             + ("" if res["has_phone"] else " No mobile column found — mobile matching will send everyone to manual review.")
                             + ("" if res["has_cnic"] else " No CNIC column found."))

    def has_add_permission(self, request):
        return request.user.has_perm("registrations.upload_dataset")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("registrations.upload_dataset")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("registrations.upload_dataset")


@admin.register(AuthorizedStudent)
class AuthorizedStudentAdmin(admin.ModelAdmin):
    """Read-only and masked: names show initials only, numbers show last 2 digits."""
    list_display = ["roll_display", "masked_name", "masked_phone", "masked_cnic", "dataset"]
    list_filter = ["dataset"]
    search_fields = ["roll_norm"]
    list_per_page = 50

    @admin.display(description="Name")
    def masked_name(self, o):
        return utils.mask_name(o.name)

    @admin.display(description="Mobile")
    def masked_phone(self, o):
        return utils.mask_value(o.phone_last4, 2) if o.phone_last4 else "—"

    @admin.display(description="CNIC")
    def masked_cnic(self, o):
        return utils.mask_value(o.cnic_last4, 2) if o.cnic_last4 else "—"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------- per-event settings
class FieldInline(admin.TabularInline):
    model = RegistrationField
    extra = 0
    fields = ["order", "label", "key", "field_type", "required", "choices", "help_text", "is_active"]
    verbose_name_plural = "Extra questions on the registration form"


class PaymentInline(admin.StackedInline):
    model = PaymentMethod
    extra = 0
    fields = [("kind", "title", "order", "is_active"), ("account_title", "account_number"), "instructions"]
    verbose_name_plural = "Payment methods (only list what you can really receive)"


@admin.register(EventRegistrationConfig)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ["event", "builtin_enabled", "caspam_verification_enabled", "price_summary", "capacity", "registered"]
    list_editable = ["builtin_enabled", "caspam_verification_enabled"]
    list_filter = ["builtin_enabled", "caspam_verification_enabled"]
    search_fields = ["event__title"]
    inlines = [FieldInline, PaymentInline]
    autocomplete_fields = []
    fieldsets = [
        ("Event", {"fields": ["event", "builtin_enabled", "capacity", "phone_mode", "pass_required"]}),
        ("CASPAM student verification & special pricing (this event only)", {
            "fields": ["caspam_verification_enabled", "dataset", "second_factor", "caspam_price", "external_price"],
            "description": "Switch this ON only for events that give CASPAM students a special price. OFF means the event never asks about CASPAM."}),
        ("Pricing when CASPAM verification is OFF", {"fields": ["standard_price"]}),
        ("Messages & payment instructions", {"fields": ["confirmation_note", "payment_instructions", "not_paid_message"]}),
    ]

    def get_readonly_fields(self, request, obj=None):
        return ["event"] if obj else []

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Prices (PKR)")
    def price_summary(self, o):
        if o.caspam_verification_enabled:
            return f"CASPAM {o.caspam_price:,.0f} / External {o.external_price:,.0f}"
        return "Free" if o.standard_price == 0 else f"{o.standard_price:,.0f}"

    @admin.display(description="Registered")
    def registered(self, o):
        return o.active_count()


class SettingsInline(admin.StackedInline):
    """Shown on the Event page (existing events only), so the ON/OFF switch sits right with the event."""
    model = EventRegistrationConfig
    can_delete = False
    max_num = 1
    verbose_name_plural = "Built-in registration & ticketing"
    fields = ["builtin_enabled", "caspam_verification_enabled", "dataset", "second_factor",
              ("caspam_price", "external_price"), "standard_price", "capacity", "full_settings"]
    readonly_fields = ["full_settings"]
    classes = ["collapse"]

    @admin.display(description="More")
    def full_settings(self, o):
        if not o.pk:
            return "-"
        return format_html('<a href="{}">Registration form questions, payment methods, messages →</a> · '
                           '<a href="{}">Registrations</a>',
                           reverse("admin:registrations_eventregistrationconfig_change", args=[o.pk]),
                           reverse("admin:registrations_registration_changelist") + f"?event__id__exact={o.event_id}")


# ---------------------------------------------------------------- registrations
@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ["reference", "full_name", "event", "category", "verification_badge", "price", "portal_status", "payment_status", "pass_state", "checked_in"]
    list_filter = ["event", "category", "verification_status", "payment_status", "state", ("checked_in_at", admin.EmptyFieldListFilter)]
    search_fields = ["reference", "full_name", "email", "phone"]
    list_select_related = ["event"]
    date_hierarchy = "created_at"
    list_per_page = 50
    actions = ["act_payment_review", "act_payment_paid", "act_payment_rejected", "act_payment_refunded",
               "act_verify_ok", "act_verify_no", "act_revoke", "act_restore", "act_cancel"]

    def get_fields(self, request, obj=None):
        base = ["reference", "event", "state", "full_name", "email", "phone", "answers_display", "category", "claimed_caspam",
                "verification_status", "verification_note", "matched_record", "price", "payment_status", "payment_method",
                "payment_reference", "payment_note", "payment_submitted_at", "payment_reviewed_by", "payment_reviewed_at",
                "pass_status", "pass_revoked_reason", "verification_code", "checked_in_at", "checked_in_by", "created_at"]
        return base

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj)      # nothing is edited by hand: every change goes through a checked action

    @admin.display(description="Extra answers")
    def answers_display(self, o):
        return format_html("<br>".join(["<b>{}</b>: {}"] * len(o.answers)), *[x for v in o.answers.values() for x in (v["label"], v["value"])]) if o.answers else "—"

    @admin.display(description="Matched dataset record")
    def matched_record(self, o):
        if not o.matched_student:
            return "—"
        if not self._request_user.has_perm("registrations.verify_student"):
            return f"{o.matched_student.roll_display} · {utils.mask_name(o.matched_student.name)}"
        return f"{o.matched_student.roll_display} · {o.matched_student.name}"

    def get_queryset(self, request):
        self._request_user = request.user
        return super().get_queryset(request)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        self._request_user = request.user
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description="Verification")
    def verification_badge(self, o):
        return o.get_verification_status_display()

    @admin.display(description="Shown to participant")
    def portal_status(self, o):
        return o.public_status[1]

    @admin.display(description="Pass")
    def pass_state(self, o):
        return o.pass_status.title()

    @admin.display(description="Entered", boolean=True)
    def checked_in(self, o):
        return o.is_checked_in

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # permission hooks for @admin.action(permissions=[...])
    def has_pay_permission(self, request):
        return request.user.has_perm("registrations.approve_payment")

    def has_verify_permission(self, request):
        return request.user.has_perm("registrations.verify_student")

    def has_pass_permission(self, request):
        return request.user.has_perm("registrations.manage_pass")

    def _each(self, request, qs, fn, ok_msg):
        done = 0
        for reg in qs:
            try:
                fn(reg)
                done += 1
            except (ValueError, services.RegistrationError) as exc:
                self.message_user(request, f"{reg.reference}: {exc}", messages.WARNING)
        if done:
            self.message_user(request, f"{done} registration(s): {ok_msg}", messages.SUCCESS)

    def _pay(self, request, qs, status, text):
        self._each(request, qs, lambda r: services.change_payment(r, status, request.user, request), text)

    @admin.action(description="Payment → mark Under Review", permissions=["pay"])
    def act_payment_review(self, request, qs):
        self._pay(request, qs, Registration.REVIEW, "marked under review")

    @admin.action(description="Payment → APPROVE (participant sees REGISTERED; pass activates)", permissions=["pay"])
    def act_payment_paid(self, request, qs):
        self._pay(request, qs, Registration.PAID, "marked paid")

    @admin.action(description="Payment → REJECT (participant sees 'Sorry, we didn't get your payment')", permissions=["pay"])
    def act_payment_rejected(self, request, qs):
        self._pay(request, qs, Registration.REJECTED, "payment rejected (participant can resubmit)")

    @admin.action(description="Payment → mark Refunded", permissions=["pay"])
    def act_payment_refunded(self, request, qs):
        self._pay(request, qs, Registration.REFUNDED, "marked refunded")

    @admin.action(description="CASPAM verification → APPROVE (discount applies)", permissions=["verify"])
    def act_verify_ok(self, request, qs):
        self._each(request, qs, lambda r: services.resolve_verification(r, True, request.user, request), "verified as CASPAM student")

    @admin.action(description="CASPAM verification → REJECT (external price)", permissions=["verify"])
    def act_verify_no(self, request, qs):
        self._each(request, qs, lambda r: services.resolve_verification(r, False, request.user, request), "treated as external participants")

    @admin.action(description="Entry pass → REVOKE", permissions=["pass"])
    def act_revoke(self, request, qs):
        self._each(request, qs, lambda r: services.set_pass_revoked(r, True, request.user, request, "Revoked from dashboard"), "pass revoked")

    @admin.action(description="Entry pass → restore", permissions=["pass"])
    def act_restore(self, request, qs):
        self._each(request, qs, lambda r: services.set_pass_revoked(r, False, request.user, request), "pass restored")

    @admin.action(description="Cancel registration (frees the seat)", permissions=["pass"])
    def act_cancel(self, request, qs):
        def go(r):
            r.state = Registration.CANCELLED
            r.save(update_fields=["state", "updated_at"])
            AuditLog.record("registration_cancelled", request, request.user, r)
        self._each(request, qs, go, "cancelled")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "action", "user", "event", "registration", "detail", "ip"]
    list_filter = ["action", "event"]
    search_fields = ["detail", "registration__reference", "user__username"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
