import datetime

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.validators import validate_image_file


class EventCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.CharField(max_length=300, blank=True)
    icon = models.CharField(max_length=40, default="bi-calendar-event", help_text="Bootstrap Icons name, e.g. bi-mic")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Event category"
        verbose_name_plural = "Event categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class EventQuerySet(models.QuerySet):
    def visible(self):
        """Published (or archived) events whose publish time has arrived."""
        now = timezone.now()
        return self.filter(status__in=[Event.PUBLISHED, Event.ARCHIVED]).filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now))

    def live(self):
        """Visible and NOT archived — what shows in normal listings."""
        return self.visible().filter(status=Event.PUBLISHED)

    def upcoming(self):
        now = timezone.now()
        return self.live().filter(Q(start_at__isnull=True) | Q(end_at__gte=now) | Q(end_at__isnull=True, start_at__gte=now))

    def past(self):
        now = timezone.now()
        return self.live().filter(start_at__isnull=False).filter(
            Q(end_at__lt=now) | Q(end_at__isnull=True, start_at__lt=now))


class Event(models.Model):
    DRAFT, PUBLISHED, ARCHIVED = "draft", "published", "archived"
    STATUS = [(DRAFT, "Draft (hidden)"), (PUBLISHED, "Published"), (ARCHIVED, "Archived")]

    title = models.CharField("Event name", max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True,
                            help_text="Web address part. Filled automatically from the name.")
    category = models.ForeignKey(EventCategory, on_delete=models.PROTECT, related_name="events")
    status = models.CharField(max_length=10, choices=STATUS, default=DRAFT)
    publish_at = models.DateTimeField("Schedule publication", null=True, blank=True,
                                      help_text="Optional. A published event stays hidden until this date/time.")
    tagline = models.CharField("Short headline", max_length=220, blank=True,
                               help_text="e.g. Welcoming the New Academic Generation")
    summary = models.TextField("Short summary", max_length=400, blank=True,
                               help_text="Shown on event cards and in search results.")
    start_at = models.DateTimeField("Date & time", null=True, blank=True)
    end_at = models.DateTimeField("Ends at", null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    cover_image = models.ImageField(upload_to="events/covers/", blank=True, validators=[validate_image_file])
    poster = models.ImageField(upload_to="events/posters/", blank=True, validators=[validate_image_file])
    description = CKEditor5Field("Detailed description", blank=True, config_name="default")
    purpose = CKEditor5Field("Purpose & objectives", blank=True, config_name="default")
    organizing_note = models.CharField("Organizing team (text)", max_length=250, blank=True,
                                       help_text="Optional extra line, e.g. 'In collaboration with …'.")
    organizers = models.ManyToManyField("team.TeamMember", blank=True, related_name="organized_events",
                                        verbose_name="Organizing team members")
    # Registration
    registration_open = models.BooleanField("Registration applies to this event", default=False)
    registration_info = CKEditor5Field("Registration details", blank=True, config_name="default")
    registration_url = models.URLField("Registration link", blank=True, help_text="e.g. a Google Form link.")
    registration_deadline = models.DateTimeField(null=True, blank=True)
    # Recap
    recap_title = models.CharField("Recap headline", max_length=220, blank=True)
    recap = CKEditor5Field("Event recap / story", blank=True, config_name="default",
                           help_text="Write this after the event. When filled, the page switches to the editorial recap layout.")
    outcomes = CKEditor5Field("Outcomes", blank=True, config_name="default")
    # Display
    is_featured = models.BooleanField("Feature on homepage", default=False)
    related_events = models.ManyToManyField("self", blank=True, symmetrical=False, verbose_name="Related events (manual)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ["-start_at", "-created_at"]

    def __str__(self):
        return self.title

    def _unique_slug(self):
        base = slugify(self.title)[:200] or "event"
        slug, n = base, 2
        while Event.objects.exclude(pk=self.pk).filter(slug=slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)
        # Every event automatically owns an album, so uploads appear in Gallery AND on the event page.
        from apps.gallery.models import Album
        Album.objects.get_or_create(event=self, defaults={
            "title": self.title, "is_published": self.status != self.DRAFT})

    def get_absolute_url(self):
        return reverse("events:detail", args=[self.slug])

    # --- state helpers ---
    @property
    def is_visible(self):
        if self.status == self.DRAFT:
            return False
        return not (self.publish_at and self.publish_at > timezone.now())

    @property
    def is_past(self):
        if not self.start_at:
            return False
        ref = self.end_at or self.start_at
        return ref < timezone.now()

    @property
    def has_recap(self):
        return bool(self.recap and self.recap.strip())

    @property
    def registration_is_open(self):
        if not self.registration_open or self.is_past:
            return False
        return not (self.registration_deadline and self.registration_deadline < timezone.now())

    @property
    def academic_year(self):
        if not self.start_at:
            return ""
        d = timezone.localtime(self.start_at)
        y = d.year if d.month >= 8 else d.year - 1
        return f"{y}-{str(y + 1)[-2:]}"

    @property
    def card_image(self):
        return self.cover_image or self.poster or None

    def related(self, limit=3):
        manual = list(self.related_events.visible().exclude(pk=self.pk)[:limit])
        if len(manual) >= limit:
            return manual
        extra = (Event.objects.live().filter(category=self.category).exclude(pk=self.pk)
                 .exclude(pk__in=[m.pk for m in manual])[: limit - len(manual)])
        return manual + list(extra)

    def duplicate(self):
        """Copy as a new DRAFT (details, highlights, speakers, organizers; not photos/videos).
        Works on a fresh copy so the original object is never modified."""
        highlights = list(self.highlights.all())
        speakers = list(self.speakers.all())
        organizers = list(self.organizers.all())
        copy = Event.objects.get(pk=self.pk)
        copy.pk = None
        copy.id = None
        copy.slug = ""
        copy.title = f"{self.title} (copy)"
        copy.status = self.DRAFT
        copy.is_featured = False
        copy.recap = copy.recap_title = copy.outcomes = ""
        copy._state.adding = True
        copy.save()
        for h in highlights:
            h.pk = None
            h.event = copy
            h.save()
        for sp in speakers:
            sp.pk = None
            sp.event = copy
            sp.save()
        copy.organizers.set(organizers)
        return copy


class EventHighlight(models.Model):
    HIGHLIGHT, ACTIVITY = "highlight", "activity"
    KIND = [(HIGHLIGHT, "Highlight / important moment"), (ACTIVITY, "Key activity")]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="highlights")
    kind = models.CharField(max_length=10, choices=KIND, default=HIGHLIGHT)
    title = models.CharField(max_length=160)
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to="events/highlights/", blank=True, validators=[validate_image_file])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["kind", "order", "id"]

    def __str__(self):
        return self.title


class EventSpeaker(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="speakers")
    name = models.CharField(max_length=120)
    role = models.CharField("Title / affiliation", max_length=200, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="events/speakers/", blank=True, validators=[validate_image_file])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Speaker / guest"

    def __str__(self):
        return self.name

    @property
    def initials(self):
        parts = [p for p in self.name.replace(".", " ").split() if p]
        return ((parts[0][0] + parts[-1][0]) if len(parts) > 1 else self.name[:2]).upper()
