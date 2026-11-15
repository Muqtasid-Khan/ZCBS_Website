from django.db import models


class InterestArea(models.Model):
    name = models.CharField(max_length=80, unique=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Area of interest"
        verbose_name_plural = "Areas of interest"

    def __str__(self):
        return self.name


class MembershipApplication(models.Model):
    PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
    STATUS = [(PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected")]
    full_name = models.CharField(max_length=120)
    registration_number = models.CharField(max_length=40)
    program = models.CharField("Academic program", max_length=100)
    semester = models.CharField(max_length=20)
    email = models.EmailField()
    phone = models.CharField("Contact number", max_length=30)
    interests = models.ManyToManyField(InterestArea, blank=True, related_name="applications")
    other_interests = models.CharField(max_length=200, blank=True)
    reason = models.TextField("Reason for joining", max_length=2000)
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING)
    admin_notes = models.TextField("Administrative notes", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Membership application"

    def __str__(self):
        return f"{self.full_name} ({self.registration_number})"
