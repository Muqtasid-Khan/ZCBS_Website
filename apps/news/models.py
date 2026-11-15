from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.validators import validate_image_file


class AnnouncementCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Announcement category"
        verbose_name_plural = "Announcement categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class AnnouncementQuerySet(models.QuerySet):
    def visible(self):
        now = timezone.now()
        return self.filter(status=Announcement.PUBLISHED).filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now))


class Announcement(models.Model):
    DRAFT, PUBLISHED, ARCHIVED = "draft", "published", "archived"
    STATUS = [(DRAFT, "Draft (hidden)"), (PUBLISHED, "Published"), (ARCHIVED, "Archived")]
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    category = models.ForeignKey(AnnouncementCategory, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="announcements")
    summary = models.CharField(max_length=300, blank=True)
    body = CKEditor5Field(blank=True, config_name="default")
    image = models.ImageField(upload_to="news/", blank=True, validators=[validate_image_file])
    status = models.CharField(max_length=10, choices=STATUS, default=DRAFT)
    publish_at = models.DateTimeField("Publication date", default=timezone.now,
                                      help_text="Future dates schedule the post.")
    is_pinned = models.BooleanField("Pinned (always on top)", default=False)
    is_featured = models.BooleanField("Featured on homepage", default=False)
    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="announcements", verbose_name="Related event",
                              help_text="Optional. Shows this notice on that event's page.")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AnnouncementQuerySet.as_manager()

    class Meta:
        ordering = ["-is_pinned", "-publish_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:220] or "update"
            slug, n = base, 2
            while Announcement.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:detail", args=[self.slug])
