"""Switch the built-in registration system (and optionally CASPAM pricing) on for one existing event.
   python manage.py configure_registration qawwali-night --caspam --dataset 1 --caspam-price 1500 --external-price 2000
   python manage.py configure_registration some-seminar --standard-price 0
The dashboard does the same; this is the quick route."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.events.models import Event
from apps.registrations.models import StudentDataset


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, p):
        p.add_argument("slug")
        p.add_argument("--caspam", action="store_true", help="turn CASPAM verification + special pricing ON")
        p.add_argument("--no-caspam", action="store_true", help="turn it OFF")
        p.add_argument("--dataset", type=int)
        p.add_argument("--caspam-price", type=Decimal, default=None)
        p.add_argument("--external-price", type=Decimal, default=None)
        p.add_argument("--standard-price", type=Decimal, default=None)

    def handle(self, *a, **o):
        try:
            ev = Event.objects.get(slug=o["slug"])
        except Event.DoesNotExist:
            raise CommandError("No event with that slug.")
        cfg = ev.reg_config
        cfg.builtin_enabled = True
        if o["caspam"]:
            cfg.caspam_verification_enabled = True
        if o["no_caspam"]:
            cfg.caspam_verification_enabled = False
        if o["dataset"]:
            cfg.dataset = StudentDataset.objects.get(pk=o["dataset"])
        for opt, attr in (("caspam_price", "caspam_price"), ("external_price", "external_price"), ("standard_price", "standard_price")):
            if o[opt] is not None:
                setattr(cfg, attr, o[opt])
        try:
            cfg.full_clean()
        except ValidationError as exc:
            raise CommandError("; ".join(sum(exc.message_dict.values(), [])))
        cfg.save()
        self.stdout.write(self.style.SUCCESS(f"{ev.title}: built-in form ON, CASPAM verification {'ON' if cfg.caspam_verification_enabled else 'OFF'}."))
