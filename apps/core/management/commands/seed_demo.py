"""OPTIONAL: adds clearly labelled [DEMO] content so you can preview the layouts.
   python manage.py seed_demo           add demo content
   python manage.py seed_demo --remove  delete it again
Nothing here is real society information."""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.events.models import Event, EventCategory, EventHighlight
from apps.news.models import Announcement

DEMO = "[DEMO] "


class Command(BaseCommand):
    help = "Add or remove clearly-labelled demo content."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true")

    def handle(self, *a, **o):
        if o["remove"]:
            Event.objects.filter(title__startswith=DEMO).delete()
            Announcement.objects.filter(title__startswith=DEMO).delete()
            self.stdout.write("Demo content removed.")
            return
        cat = EventCategory.objects.first()
        now = timezone.now()
        past = Event.objects.create(
            title=DEMO + "Sample Past Event", category=cat, status="published", is_featured=True,
            start_at=now - datetime.timedelta(days=30), venue="Sample venue",
            tagline="A sample recap layout", summary="Demo content showing how a past event story looks.",
            recap_title="A sample event story", recap="<p>This is demo text. Replace it with your real recap.</p>",
            description="<p>Demo description.</p>")
        EventHighlight.objects.create(event=past, title="Sample highlight", text="Demo text.")
        Event.objects.create(title=DEMO + "Sample Upcoming Event", category=cat, status="published", is_featured=True,
                             start_at=now + datetime.timedelta(days=14), venue="Sample venue",
                             summary="Demo content showing an upcoming-event layout.", registration_open=True)
        Announcement.objects.create(title=DEMO + "Sample announcement", status="published", is_pinned=True,
                                    summary="Demo announcement.", body="<p>Demo body text.</p>")
        self.stdout.write("Demo content added. Remove with: python manage.py seed_demo --remove")
