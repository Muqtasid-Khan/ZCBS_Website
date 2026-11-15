from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin import SortableMixin
from .models import TeamCategory, TeamMember


@admin.register(TeamCategory)
class TeamCategoryAdmin(SortableMixin, admin.ModelAdmin):
    list_display = ["name", "order", "is_visible"]
    list_editable = ["order", "is_visible"]
    prepopulated_fields = {"slug": ["name"]}


@admin.action(description="Feature selected profiles")
def feature(modeladmin, request, qs):
    qs.update(is_featured=True)


@admin.action(description="Un-feature selected profiles")
def unfeature(modeladmin, request, qs):
    qs.update(is_featured=False)


@admin.action(description="Hide selected from website")
def hide(modeladmin, request, qs):
    qs.update(is_active=False)


@admin.action(description="Show selected on website")
def show(modeladmin, request, qs):
    qs.update(is_active=True)


@admin.register(TeamMember)
class TeamMemberAdmin(SortableMixin, admin.ModelAdmin):
    list_display = ["avatar", "name", "designation", "category", "class_label", "tenure", "order", "is_active"]
    list_display_links = ["avatar", "name"]
    list_editable = ["designation", "category", "order", "is_active"]
    list_filter = ["category", "tenure", "is_active", "is_featured"]
    search_fields = ["name", "designation", "class_label", "program"]
    actions = [feature, unfeature, show, hide]
    readonly_fields = ["photo_preview"]
    list_per_page = 50
    fieldsets = [
        ("Who", {"fields": ["name", "designation", "category", "tenure"]}),
        ("Academic information", {"fields": ["program", "class_label"]}),
        ("Photograph", {"fields": ["photo", "photo_preview"]}),
        ("Profile", {"fields": ["bio", "is_featured", "is_active", "order"]}),
        ("Links (optional)", {"fields": ["email", "linkedin_url", "instagram_url", "facebook_url"]}),
    ]

    @admin.display(description="")
    def avatar(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width:38px;height:38px;border-radius:50%;object-fit:cover">', obj.photo.url)
        return format_html('<span style="display:inline-flex;width:38px;height:38px;border-radius:50%;align-items:center;'
                           'justify-content:center;background:hsl({},35%,28%);color:#fff;font-weight:600;font-size:13px">{}</span>',
                           obj.avatar_hue, obj.initials)

    @admin.display(description="Current photo")
    def photo_preview(self, obj):
        if obj.pk and obj.photo:
            return format_html('<img src="{}" style="max-height:160px;border-radius:8px">', obj.photo.url)
        return "No photograph yet — an initials avatar is shown on the website."
