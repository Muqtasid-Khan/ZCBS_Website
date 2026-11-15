from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from apps.core.admin import SortableMixin
from apps.core.validators import validate_image_file
from apps.events.models import Event
from .models import Album, MediaCategory, MediaItem


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        files = data if isinstance(data, (list, tuple)) else [data]
        out = []
        for f in files:
            if f:
                out.append(single(f, initial))
        if not out and self.required:
            raise ValidationError("Choose at least one photograph.")
        return out


class BulkUploadForm(forms.Form):
    photos = MultipleImageField(label="Photographs (select many)")
    event = forms.ModelChoiceField(Event.objects.all(), required=False, help_text="Photos will appear on this event's page AND in its gallery album.")
    album = forms.ModelChoiceField(Album.objects.all(), required=False, help_text="Or choose an album that is not tied to an event.")
    category = forms.ModelChoiceField(MediaCategory.objects.all(), required=False)
    is_published = forms.BooleanField(required=False, initial=True, label="Publish immediately")

    def clean(self):
        data = super().clean()
        for f in data.get("photos", []):
            validate_image_file(f)
        return data


@admin.register(MediaCategory)
class MediaCategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    prepopulated_fields = {"slug": ["name"]}


class AlbumItemInline(admin.TabularInline):
    model = MediaItem
    fk_name = "album"
    extra = 0
    fields = ["kind", "image", "video_url", "caption", "category", "order", "is_published"]
    show_change_link = True


@admin.register(Album)
class AlbumAdmin(SortableMixin, admin.ModelAdmin):
    list_display = ["title", "event", "date", "photo_count", "is_published", "order"]
    list_editable = ["is_published", "order"]
    list_filter = ["is_published"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [AlbumItemInline]

    @admin.display(description="Items")
    def photo_count(self, obj):
        return obj.items.count()


@admin.action(description="Publish selected")
def pub(modeladmin, request, qs):
    qs.update(is_published=True)


@admin.action(description="Hide selected")
def unpub(modeladmin, request, qs):
    qs.update(is_published=False)


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    """The Media Library."""
    change_list_template = "admin/gallery/mediaitem/change_list.html"
    list_display = ["thumb_tag", "caption", "kind", "album", "event", "category", "uploaded_at", "is_published"]
    list_display_links = ["thumb_tag", "caption"]
    list_editable = ["is_published"]
    list_filter = ["kind", "is_published", "album", "event", "category"]
    search_fields = ["caption", "album__title", "event__title"]
    list_per_page = 40
    actions = [pub, unpub]
    fieldsets = [
        ("Media", {"fields": ["kind", "image", "video_file", "video_url", "caption"]}),
        ("Where it appears", {"fields": ["event", "album", "category", "order", "is_published"]}),
    ]

    @admin.display(description="Preview")
    def thumb_tag(self, obj):
        if obj.kind == "photo" and obj.image:
            return format_html('<img src="{}" style="height:46px;width:70px;object-fit:cover;border-radius:4px">', obj.image.url)
        return "▶ video"

    def get_urls(self):
        return [path("bulk-upload/", self.admin_site.admin_view(self.bulk_upload), name="gallery_mediaitem_bulk")] + super().get_urls()

    def bulk_upload(self, request):
        if not self.has_add_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        initial = {}
        if request.GET.get("event"):
            initial["event"] = request.GET["event"]
        if request.GET.get("album"):
            initial["album"] = request.GET["album"]
        form = BulkUploadForm(request.POST or None, request.FILES or None, initial=initial)
        if request.method == "POST" and form.is_valid():
            d = form.cleaned_data
            n = 0
            for f in d["photos"]:
                MediaItem.objects.create(kind="photo", image=f, event=d["event"], album=d["album"],
                                         category=d["category"], is_published=d["is_published"])
                n += 1
            messages.success(request, f"{n} photograph(s) uploaded.")
            return redirect("admin:gallery_mediaitem_changelist")
        ctx = {**self.admin_site.each_context(request), "form": form, "title": "Upload many photographs",
               "opts": self.model._meta}
        return render(request, "admin/gallery/bulk_upload.html", ctx)
