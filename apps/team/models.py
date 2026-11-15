from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.validators import validate_image_file


class TeamCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.CharField(max_length=250, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Team category"
        verbose_name_plural = "Team categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TeamMember(models.Model):
    category = models.ForeignKey(TeamCategory, on_delete=models.PROTECT, related_name="members")
    name = models.CharField("Full name", max_length=120)
    designation = models.CharField("Official designation", max_length=100)
    program = models.CharField("Academic program", max_length=80, blank=True, help_text="e.g. BS AI")
    class_label = models.CharField("Class / session", max_length=40, blank=True, help_text="e.g. BS 2023-27")
    photo = models.ImageField(upload_to="team/", blank=True, validators=[validate_image_file],
                              help_text="Optional. A clean initials avatar is shown until a photo is uploaded.")
    bio = models.TextField("Short biography", blank=True)
    email = models.EmailField(blank=True)
    linkedin_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    is_featured = models.BooleanField("Featured profile", default=False)
    is_active = models.BooleanField("Show on website", default=True)
    order = models.PositiveIntegerField("Display order", default=0)
    tenure = models.CharField("Tenure", max_length=20, default="2026-2027",
                              help_text="Used for the leadership-transition archive, e.g. 2026-2027.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category__order", "order", "id"]

    def __str__(self):
        return f"{self.name} — {self.designation}"

    @property
    def initials(self):
        parts = [p for p in self.name.replace(".", " ").split() if p]
        if not parts:
            return "Z"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def academic_line(self):
        bits = [b for b in (self.program, self.class_label) if b]
        return " · ".join(bits)

    @property
    def avatar_hue(self):
        return sum(ord(c) for c in self.name) % 360

    @property
    def socials(self):
        out = []
        if self.linkedin_url: out.append(("bi-linkedin", self.linkedin_url, "LinkedIn"))
        if self.instagram_url: out.append(("bi-instagram", self.instagram_url, "Instagram"))
        if self.facebook_url: out.append(("bi-facebook", self.facebook_url, "Facebook"))
        if self.email: out.append(("bi-envelope", "mailto:" + self.email, "Email"))
        return out
