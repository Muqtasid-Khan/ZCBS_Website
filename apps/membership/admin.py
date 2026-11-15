from django.contrib import admin, messages
from django.utils import timezone

from apps.core.admin import export_csv
from .models import InterestArea, MembershipApplication
from .notifications import DECISION_STATUSES, send_decision_emails


@admin.register(InterestArea)
class InterestAreaAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_active"]
    list_editable = ["order", "is_active"]


def _report_emails(modeladmin, request, sent, failed):
    if sent:
        modeladmin.message_user(request, f"{sent} email(s) sent to the applicant(s).")
    if failed:
        modeladmin.message_user(
            request,
            f"{failed} email(s) could NOT be sent. The decision was saved - please contact "
            "the applicant manually (email settings may be missing).",
            level=messages.WARNING)


def _set(status):
    def action(modeladmin, request, qs):
        # Only applications whose status really changes are updated and emailed,
        # so nobody receives the same email twice.
        changing_ids = list(qs.exclude(status=status).values_list("pk", flat=True))
        MembershipApplication.objects.filter(pk__in=changing_ids).update(
            status=status, reviewed_at=timezone.now(), reviewed_by=request.user)
        modeladmin.message_user(request, f"{len(changing_ids)} application(s) marked {status}.")
        if status in DECISION_STATUSES and changing_ids:
            sent, failed = send_decision_emails(
                MembershipApplication.objects.filter(pk__in=changing_ids))
            _report_emails(modeladmin, request, sent, failed)
    action.__name__ = f"mark_{status}"
    action.short_description = f"Mark selected as {status.upper()}"
    return action


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = ["full_name", "registration_number", "program", "semester", "email", "phone", "status", "created_at"]
    list_filter = ["status", "program", "semester", "created_at", "interests"]
    search_fields = ["full_name", "registration_number", "email", "phone", "program"]
    date_hierarchy = "created_at"
    actions = [_set("approved"), _set("rejected"), _set("pending"), export_csv]
    readonly_fields = ["full_name", "registration_number", "program", "semester", "email", "phone", "interests",
                       "other_interests", "reason", "created_at", "reviewed_at", "reviewed_by"]
    fieldsets = [
        ("Applicant", {"fields": ["full_name", "registration_number", "program", "semester", "email", "phone"]}),
        ("Application", {"fields": ["interests", "other_interests", "reason", "created_at"]}),
        ("Decision", {"fields": ["status", "admin_notes", "reviewed_by", "reviewed_at"]}),
    ]

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        status_changed = change and "status" in form.changed_data
        if status_changed:
            obj.reviewed_at = timezone.now()
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)
        if status_changed and obj.status in DECISION_STATUSES:
            sent, failed = send_decision_emails([obj])
            _report_emails(self, request, sent, failed)
