from django.contrib import admin
from django.utils import timezone

from apps.core.admin import export_csv
from .models import InterestArea, MembershipApplication


@admin.register(InterestArea)
class InterestAreaAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_active"]
    list_editable = ["order", "is_active"]


def _set(status):
    def action(modeladmin, request, qs):
        qs.update(status=status, reviewed_at=timezone.now(), reviewed_by=request.user)
        modeladmin.message_user(request, f"{qs.count()} application(s) marked {status}.")
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
        if change and "status" in form.changed_data:
            obj.reviewed_at = timezone.now()
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)
