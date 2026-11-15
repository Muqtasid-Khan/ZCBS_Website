"""Emails sent to applicants when their membership decision is recorded."""
import logging

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from apps.core.models import SiteSettings

logger = logging.getLogger(__name__)

DECISION_STATUSES = ("approved", "rejected")


def _signature(site):
    return (f"{site.site_name} ({site.short_name})\n"
            "CASPAM Chapter, Bahauddin Zakariya University, Multan")


def build_decision_email(application, site=None):
    """Return an EmailMessage for an approved/rejected application, or None."""
    if application.status not in DECISION_STATUSES or not application.email:
        return None
    site = site or SiteSettings.load()
    website = f"\n\nWebsite: {settings.SITE_URL}" if getattr(settings, "SITE_URL", "") else ""

    if application.status == "approved":
        subject = f"Your {site.short_name} membership application has been approved"
        body = (f"Dear {application.full_name},\n\n"
                f"We are pleased to let you know that your membership application to "
                f"{site.site_name} ({site.short_name}) has been approved. Welcome!\n\n"
                "Please keep an eye on our website for upcoming events and announcements."
                f"{website}\n\nWith best regards,\n{_signature(site)}\n")
    else:
        subject = f"Update on your {site.short_name} membership application"
        body = (f"Dear {application.full_name},\n\n"
                f"Thank you for your interest in {site.site_name} ({site.short_name}). "
                "After reviewing your application, we are unable to offer you membership at this time.\n\n"
                "We appreciate the time you took to apply and welcome you to follow our "
                f"events and announcements.{website}\n\nWith best regards,\n{_signature(site)}\n")

    reply_to = [site.contact_email] if site.contact_email else None
    return EmailMessage(subject=subject, body=body, to=[application.email], reply_to=reply_to)


def send_decision_emails(applications):
    """Send decision emails over one connection. Returns (sent, failed). Never raises."""
    site = SiteSettings.load()
    messages = [m for m in (build_decision_email(a, site) for a in applications) if m]
    if not messages:
        return 0, 0
    if settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
        # Email is not configured: messages would only be printed to the server log.
        logger.warning("Email is not configured (no EMAIL_HOST_USER/EMAIL_HOST_PASSWORD); nothing was delivered")
        return 0, len(messages)
    sent = 0
    try:
        connection = get_connection()
        connection.open()
    except Exception:
        logger.exception("Could not open the email connection")
        return 0, len(messages)
    try:
        for message in messages:
            message.connection = connection
            try:
                sent += message.send() or 0
            except Exception:
                logger.exception("Could not send decision email to %s", message.to)
    finally:
        try:
            connection.close()
        except Exception:
            pass
    return sent, len(messages) - sent
