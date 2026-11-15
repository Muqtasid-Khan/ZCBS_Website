import re

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.validators import validate_image_file, validate_video_file, video_storage


class MediaCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Media category"
        verbose_name_plural = "Media categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Album(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover = models.ImageField("Album cover", upload_to="albums/", blank=True, validators=[validate_image_file],
                              help_text="Optional. The first photo is used if empty.")
    event = models.OneToOneField("events.Event", null=True, blank=True, on_delete=models.CASCADE, related_name="album",
                                 help_text="Linked automatically for event albums.")
    date = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-date", "-id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "album"
            slug, n = base, 2
            while Album.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("gallery:album", args=[self.slug])

    @property
    def cover_image(self):
        if self.cover:
            return self.cover
        first = self.items.filter(kind=MediaItem.PHOTO, is_published=True).exclude(image="").first()
        if first:
            return first.image
        if self.event and self.event.card_image:
            return self.event.card_image
        return None


YT = re.compile(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([\w-]{11})")
VIMEO = re.compile(r"vimeo\.com/(?:video/)?(\d+)")


class MediaItem(models.Model):
    PHOTO, VIDEO = "photo", "video"
    KIND = [(PHOTO, "Photograph"), (VIDEO, "Video")]
    kind = models.CharField(max_length=6, choices=KIND, default=PHOTO)
    image = models.ImageField(upload_to="gallery/", blank=True, validators=[validate_image_file])
    video_file = models.FileField(upload_to="gallery/videos/", blank=True, storage=video_storage,
                                  validators=[validate_video_file])
    video_url = models.URLField("Video link (YouTube / Vimeo)", blank=True)
    caption = models.CharField(max_length=300, blank=True)
    album = models.ForeignKey(Album, null=True, blank=True, on_delete=models.SET_NULL, related_name="items")
    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.SET_NULL, related_name="media")
    category = models.ForeignKey(MediaCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="items")
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-uploaded_at", "-id"]
        verbose_name = "Media item"

    def __str__(self):
        return self.caption or f"{self.get_kind_display()} #{self.pk}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.kind == self.PHOTO and not self.image:
            raise ValidationError({"image": "Please upload a photograph."})
        if self.kind == self.VIDEO and not (self.video_file or self.video_url):
            raise ValidationError("For a video, upload a file or paste a YouTube/Vimeo link.")
        if self.video_url and not (YT.search(self.video_url) or VIMEO.search(self.video_url)):
            raise ValidationError({"video_url": "Only YouTube and Vimeo links are supported."})

    def save(self, *args, **kwargs):
        # Link to the event's album automatically so nothing has to be uploaded twice.
        if self.event_id and not self.album_id:
            album = getattr(self.event, "album", None)
            if album:
                self.album = album
        elif self.album_id and not self.event_id and self.album.event_id:
            self.event_id = self.album.event_id
        super().save(*args, **kwargs)

    @property
    def embed_url(self):
        m = YT.search(self.video_url or "")
        if m:
            return f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
        m = VIMEO.search(self.video_url or "")
        if m:
            return f"https://player.vimeo.com/video/{m.group(1)}"
        return ""

    @property
    def thumb(self):
        if self.kind == self.PHOTO and self.image:
            return self.image
        return None
