from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from .validators import validate_image_file

hex_color = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a colour like #0B1B2E")


class SiteSettings(models.Model):
    """One row only. Every global setting of the website lives here."""
    # Identity
    site_name = models.CharField(max_length=120, default="Zakariyan Character Building Society")
    short_name = models.CharField(max_length=20, default="ZCBS")
    chapter_line = models.CharField("Chapter", max_length=120, default="CASPAM Chapter")
    institution = models.CharField(max_length=160, default="Bahauddin Zakariya University, Multan")
    tagline = models.CharField(max_length=200, blank=True, default="Building character. Developing leaders.")
    logo = models.ImageField("Logo override", upload_to="branding/", blank=True, validators=[validate_image_file],
                             help_text="Optional. Leave empty to use the built-in ZCBS logo. Use a PNG with transparent background.")
    favicon = models.ImageField("Favicon override", upload_to="branding/", blank=True, validators=[validate_image_file],
                                help_text="Optional square image (PNG), at least 128×128.")
    # Colours
    primary_color = models.CharField(max_length=7, default="#0B1B2E", validators=[hex_color],
                                     help_text="Main dark colour (navy) used on the hero, footer and headings.")
    accent_color = models.CharField(max_length=7, default="#C9A24B", validators=[hex_color],
                                    help_text="Accent (gold) used on buttons, lines and highlights.")
    # Contact
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=250, blank=True)
    map_embed_url = models.URLField(blank=True, help_text="Google Maps 'Embed a map' link (src only). Optional.")
    contact_intro = models.TextField(blank=True, help_text="Short text shown above the contact form.")
    # Social
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    x_url = models.URLField("X (Twitter) URL", blank=True)
    whatsapp_url = models.URLField("WhatsApp channel/group URL", blank=True)
    tiktok_url = models.URLField("TikTok URL", blank=True)
    # SEO
    seo_title = models.CharField(max_length=70, blank=True, help_text="Browser/Google title for the homepage.")
    seo_description = models.CharField(max_length=170, blank=True)
    og_image = models.ImageField("Social sharing image", upload_to="branding/", blank=True, validators=[validate_image_file],
                                 help_text="Shown when links are shared on WhatsApp/Facebook. 1200×630 is ideal.")
    analytics_id = models.CharField("Google Analytics ID", max_length=30, blank=True,
                                    help_text="Optional, like G-XXXXXXXXXX. Nothing is tracked while this is empty.")
    # Footer & features
    footer_text = models.CharField(max_length=250, blank=True)
    enable_intro = models.BooleanField("Show cinematic intro", default=True)
    intro_once_per_visitor = models.BooleanField(
        "Play intro only on a visitor's first visit", default=True,
        help_text="Remembers in the visitor's own browser (no tracking, nothing sent to the server).")
    show_stats = models.BooleanField("Show activity summary on homepage", default=True,
                                     help_text="Real counts taken from the database. Never invented.")
    membership_open = models.BooleanField("Membership applications open", default=True)
    membership_intro = CKEditor5Field(blank=True, config_name="default")
    newsletter_enabled = models.BooleanField("Show newsletter sign-up", default=True)
    show_pending_publicly = models.BooleanField(
        "Show 'pending approval' text to the public", default=False,
        help_text="Keep OFF. Drafted vision/mission text stays hidden from visitors until you approve it.")

    class Meta:
        verbose_name = "Website settings"
        verbose_name_plural = "Website settings"

    def __str__(self):
        return "Website settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        kwargs["force_insert"] = False  # always update-or-create the single row
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # the single settings row cannot be deleted

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def socials(self):
        items = [("facebook", "bi-facebook", self.facebook_url), ("instagram", "bi-instagram", self.instagram_url),
                 ("linkedin", "bi-linkedin", self.linkedin_url), ("youtube", "bi-youtube", self.youtube_url),
                 ("x", "bi-twitter-x", self.x_url), ("whatsapp", "bi-whatsapp", self.whatsapp_url)]
        return [{"name": n, "icon": i, "url": u} for n, i, u in items if u]


class HomeSection(models.Model):
    """A block on the homepage. Reorder, hide, retitle and edit text from the dashboard."""
    KEYS = [
        ("hero", "Hero (top banner)"), ("about", "About ZCBS preview"), ("vision_mission", "Vision & mission"),
        ("objectives", "Core objectives"), ("stats", "Activity summary"), ("upcoming_events", "Featured upcoming events"),
        ("recent_events", "Recent event highlights"), ("announcements", "Latest announcements"),
        ("leadership", "Leadership preview"), ("core_team", "Core team preview"), ("media_team", "Media team preview"),
        ("gallery", "Gallery highlights"), ("membership", "Membership invitation"), ("social", "Social media"),
    ]
    key = models.CharField(max_length=30, choices=KEYS, unique=True)
    eyebrow = models.CharField("Small label above heading", max_length=80, blank=True)
    heading = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    button_label = models.CharField(max_length=60, blank=True)
    button_url = models.CharField(max_length=300, blank=True, help_text="Page path like /about/ or a full web address.")
    image = models.ImageField(upload_to="home/", blank=True, validators=[validate_image_file],
                              help_text="Optional picture for this section (used by Hero and About).")
    is_visible = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Homepage section"

    def __str__(self):
        return self.get_key_display()


class NavItem(models.Model):
    HEADER, FOOTER = "header", "footer"
    label = models.CharField(max_length=60)
    url = models.CharField(max_length=300, help_text="Page path like /events/ or a full web address.")
    location = models.CharField(max_length=10, choices=[(HEADER, "Top menu"), (FOOTER, "Footer")], default=HEADER)
    order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    open_in_new_tab = models.BooleanField(default=False)

    class Meta:
        ordering = ["location", "order", "id"]
        verbose_name = "Menu link"

    def __str__(self):
        return f"{self.label} ({self.get_location_display()})"


APPROVAL = [("pending", "Pending approval"), ("approved", "Approved")]


class PageContent(models.Model):
    """Editable page text (e.g. the About introduction)."""
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=250, blank=True)
    body = CKEditor5Field(blank=True, config_name="default")
    hero_image = models.ImageField(upload_to="pages/", blank=True, validators=[validate_image_file])
    seo_description = models.CharField(max_length=170, blank=True)
    approval = models.CharField(max_length=10, choices=APPROVAL, default="approved")

    class Meta:
        verbose_name = "Page text"
        verbose_name_plural = "Page texts"

    def __str__(self):
        return self.title


class ContentBlock(models.Model):
    """Vision, mission, objectives, values, etc. Drafted text starts as 'pending approval'."""
    KINDS = [("vision", "Vision"), ("mission", "Mission"), ("objective", "Objective"), ("value", "Core value"),
             ("approach", "Character-building approach"), ("leadership", "Leadership philosophy"),
             ("development", "Student development"), ("purpose", "Activities & purpose")]
    kind = models.CharField(max_length=20, choices=KINDS)
    title = models.CharField(max_length=160)
    text = models.TextField()
    icon = models.CharField(max_length=40, blank=True, default="bi-stars",
                            help_text="Bootstrap Icons name, e.g. bi-compass (see icons.getbootstrap.com).")
    approval = models.CharField(max_length=10, choices=APPROVAL, default="pending")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["kind", "order", "id"]
        verbose_name = "About content block"

    def __str__(self):
        return f"{self.get_kind_display()}: {self.title}"


class ContactSubmission(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField("Handled", default=False)
    notes = models.TextField("Internal notes", blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact message"

    def __str__(self):
        return f"{self.name} — {self.subject}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
