import csv

from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from .models import (ContactSubmission, ContentBlock, HomeSection, NavItem, NewsletterSubscriber, PageContent,
                     SiteSettings)


class SortableMixin:
    """Adds drag-to-reorder on the list page (then press Save) for models with an `order` column."""
    class Media:
        js = ("admin/js/zcbs_sortable.js",)


def export_csv(modeladmin, request, queryset):
    meta = modeladmin.model._meta
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{meta.model_name}.csv"'
    w = csv.writer(resp)
    fields = [f for f in meta.fields]
    w.writerow([f.verbose_name for f in fields])
    for obj in queryset:
        w.writerow([str(getattr(obj, f.name) if not f.is_relation else (getattr(obj, f.name) or "")) for f in fields])
    return resp
export_csv.short_description = "Export selected to CSV (Excel)"


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Identity", {"fields": ["site_name", "short_name", "chapter_line", "institution", "tagline"]}),
        ("Logo & colours", {"fields": ["logo", "favicon", "primary_color", "accent_color"]}),
        ("Contact details", {"fields": ["contact_email", "contact_phone", "address", "map_embed_url", "contact_intro"]}),
        ("Social media", {"fields": ["facebook_url", "instagram_url", "linkedin_url", "youtube_url", "x_url", "whatsapp_url", "tiktok_url"]}),
        ("Search engines & sharing (SEO)", {"fields": ["seo_title", "seo_description", "og_image", "analytics_id"]}),
        ("Footer & features", {"fields": ["footer_text", "enable_intro", "intro_once_per_visitor", "show_stats",
                                          "membership_open", "membership_intro", "newsletter_enabled",
                                          "show_pending_publicly"]}),
    ]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return HttpResponseRedirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))


@admin.register(HomeSection)
class HomeSectionAdmin(SortableMixin, admin.ModelAdmin):
    list_display = ["__str__", "heading", "is_visible", "order"]
    list_editable = ["is_visible", "order"]
    ordering = ["order"]
    fieldsets = [(None, {"fields": ["key", "is_visible", "order"]}),
                 ("Content", {"fields": ["eyebrow", "heading", "body", "button_label", "button_url", "image"]})]
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NavItem)
class NavItemAdmin(SortableMixin, admin.ModelAdmin):
    list_display = ["label", "url", "location", "order", "is_visible"]
    list_editable = ["order", "is_visible"]
    list_filter = ["location"]


@admin.action(description="Mark selected as APPROVED (public)")
def approve(modeladmin, request, queryset):
    n = queryset.update(approval="approved")
    modeladmin.message_user(request, f"{n} item(s) approved and now visible to visitors.")


@admin.action(description="Mark selected as PENDING approval (hide from public)")
def unapprove(modeladmin, request, queryset):
    n = queryset.update(approval="pending")
    modeladmin.message_user(request, f"{n} item(s) set back to pending.")


@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "approval"]
    list_editable = ["approval"]
    actions = [approve, unapprove]


@admin.register(ContentBlock)
class ContentBlockAdmin(SortableMixin, admin.ModelAdmin):
    list_display = ["title", "kind", "approval", "order"]
    list_editable = ["approval", "order"]
    list_filter = ["kind", "approval"]
    search_fields = ["title", "text"]
    actions = [approve, unapprove]


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "email", "created_at", "is_handled"]
    list_filter = ["is_handled"]
    search_fields = ["name", "email", "subject", "message"]
    readonly_fields = ["name", "email", "subject", "message", "created_at"]
    list_editable = ["is_handled"]
    actions = [export_csv]

    def has_add_permission(self, request):
        return False


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ["email", "created_at", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["email"]
    actions = [export_csv]
