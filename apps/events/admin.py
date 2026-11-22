from django import forms
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from apps.core.admin import SortableMixin
from apps.gallery.models import MediaItem
from .models import Event, EventCategory, EventHighlight, EventSpeaker


@admin.register(EventCategory)
class EventCategoryAdmin(SortableMixin, admin.ModelAdmin):
    list_display = ["name", "icon", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}


class HighlightInline(admin.StackedInline):
    model = EventHighlight
    extra = 0
    fields = [("kind", "title", "order"), "text", "image"]
    verbose_name = "Highlight or key activity"
    verbose_name_plural = "Event highlights & key activities"
    classes = ["collapse"]


class SpeakerInline(admin.StackedInline):
    model = EventSpeaker
    extra = 0
    fields = [("name", "role", "order"), "bio", "photo"]
    classes = ["collapse"]


class MediaInline(admin.StackedInline):
    model = MediaItem
    fk_name = "event"
    extra = 0
    fields = [("kind", "is_published", "order"), "image", ("video_file", "video_url"), "caption", "category"]
    verbose_name = "Photo / video"
    verbose_name_plural = "Event gallery (photos & videos)"
    classes = ["collapse"]


@admin.action(description="Publish selected events")
def publish(modeladmin, request, qs):
    qs.update(status=Event.PUBLISHED)
    for e in qs:
        e.album.__class__.objects.filter(event=e).update(is_published=True)


@admin.action(description="Move selected events to Archive")
def archive(modeladmin, request, qs):
    qs.update(status=Event.ARCHIVED)


@admin.action(description="Set selected events back to Draft")
def draft(modeladmin, request, qs):
    qs.update(status=Event.DRAFT)


@admin.action(description="Feature on homepage")
def feature(modeladmin, request, qs):
    qs.update(is_featured=True)


@admin.action(description="Remove from homepage features")
def unfeature(modeladmin, request, qs):
    qs.update(is_featured=False)


@admin.action(description="Duplicate selected events (as drafts)")
def duplicate(modeladmin, request, qs):
    n = 0
    for e in qs:
        e.duplicate()
        n += 1
    modeladmin.message_user(request, f"{n} event(s) duplicated as drafts. Photos and videos are not copied.", messages.SUCCESS)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    change_list_template = "admin/events/event/change_list.html"
    list_display = ["title", "category", "start_at", "venue", "status", "is_featured", "page"]
    list_editable = ["status", "is_featured"]
    list_filter = ["status", "category", "is_featured", "start_at"]
    search_fields = ["title", "tagline", "venue", "summary"]
    date_hierarchy = "start_at"
    prepopulated_fields = {"slug": ["title"]}
    filter_horizontal = ["organizers", "related_events"]
    inlines = [HighlightInline, SpeakerInline, MediaInline]

    def get_inline_instances(self, request, obj=None):
        from apps.registrations.admin import SettingsInline
        inst = super().get_inline_instances(request, obj)
        if obj is not None:      # the registration settings row is created automatically when the event is first saved
            inst.append(SettingsInline(self.model, self.admin_site))
        return inst
    actions = [publish, archive, draft, feature, unfeature, duplicate]
    readonly_fields = ["page_link", "upload_link"]
    save_on_top = True
    view_on_site = True
    fieldsets = [
        ("1 · The basics", {"fields": ["title", "category", "status", "start_at", "end_at", "venue", "tagline", "summary"]}),
        ("2 · Pictures", {"fields": ["cover_image", "poster"]}),
        ("3 · Description & purpose", {"fields": ["description", "purpose"]}),
        ("4 · Organizing team", {"fields": ["organizers", "organizing_note"]}),
        ("5 · Registration (optional)", {"fields": ["registration_open", "registration_info", "registration_url",
                                                    "registration_deadline"], "classes": ["collapse"]}),
        ("6 · Event recap (write after the event)", {"fields": ["recap_title", "recap", "outcomes"], "classes": ["collapse"]}),
        ("7 · Display & links", {"fields": ["is_featured", "publish_at", "related_events", "slug", "page_link", "upload_link"],
                                 "classes": ["collapse"]}),
    ]

    @admin.display(description="Page")
    def page(self, obj):
        return format_html('<a href="{}" target="_blank">Open ↗</a>', obj.get_absolute_url())

    @admin.display(description="Public page address")
    def page_link(self, obj):
        if not obj.pk:
            return "Created automatically when you save."
        return format_html('<a href="{0}" target="_blank">{0}</a>', obj.get_absolute_url())

    @admin.display(description="Photo upload")
    def upload_link(self, obj):
        if not obj.pk:
            return "Save the event first, then upload photos."
        url = reverse("admin:gallery_mediaitem_bulk") + f"?event={obj.pk}"
        return format_html('<a class="button" href="{}">Upload many photos at once →</a>', url)
