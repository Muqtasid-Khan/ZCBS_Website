from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin import SortableMixin
from .models import Announcement, AnnouncementCategory


@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(SortableMixin, admin.ModelAdmin):
    list_display = ["name", "order"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ["name"]}


@admin.action(description="Publish selected")
def publish(modeladmin, request, qs):
    qs.update(status="published")


@admin.action(description="Archive selected")
def archive(modeladmin, request, qs):
    qs.update(status="archived")


@admin.action(description="Pin selected")
def pin(modeladmin, request, qs):
    qs.update(is_pinned=True)


@admin.action(description="Unpin selected")
def unpin(modeladmin, request, qs):
    qs.update(is_pinned=False)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "status", "is_pinned", "is_featured", "publish_at"]
    list_editable = ["status", "is_pinned", "is_featured"]
    list_filter = ["status", "category", "is_pinned", "is_featured"]
    search_fields = ["title", "summary", "body"]
    date_hierarchy = "publish_at"
    prepopulated_fields = {"slug": ["title"]}
    actions = [publish, archive, pin, unpin]
    save_on_top = True
    view_on_site = True
    fieldsets = [
        (None, {"fields": ["title", "category", "status", "publish_at", "summary", "body", "image"]}),
        ("Options", {"fields": ["is_pinned", "is_featured", "event", "slug"]}),
    ]
