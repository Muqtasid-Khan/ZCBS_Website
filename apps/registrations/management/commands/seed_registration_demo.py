"""Creates clearly-labelled FICTIONAL demo events + a fictional student list, to try the registration system.
   python manage.py seed_registration_demo           # create
   python manage.py seed_registration_demo --remove  # delete everything it made (refuses if real people registered)"""
import io
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.registrations import services
from apps.registrations.models import PaymentMethod, RegistrationField, StudentDataset

TAG = "[DEMO] "
DATA = ("Roll No,Student Name,CNIC,WhatsApp\n"
        "DEMO-001,Aisha Demo Khan,3520100000001,0300 0000001\n"
        "DEMO-002,Bilal Demo Ahmed,3520100000002,0300 0000002\n"
        "DEMO-003,Carol Demo Noor,3520100000003,0300 0000003\n")


class Command(BaseCommand):
    help = "Create (or --remove) fictional demo events for the registration system."

    def add_arguments(self, p):
        p.add_argument("--remove", action="store_true")

    def handle(self, *a, remove=False, **o):
        if remove:
            from apps.registrations.models import Registration
            evs = Event.objects.filter(title__startswith=TAG)
            if Registration.objects.filter(event__in=evs).exists():
                raise CommandError("Demo events have registrations. Delete those first (they may be test sign-ups).")
            evs.delete()
            StudentDataset.objects.filter(name__startswith=TAG).delete()
            self.stdout.write("Demo data removed.")
            return
        cat = EventCategory.objects.first()
        ds = StudentDataset.objects.create(name=TAG + "Fictional CASPAM students", is_test_data=True)
        services.import_dataset(ds, SimpleUploadedFile("demo.csv", DATA.encode()))
        when = timezone.now() + timezone.timedelta(days=21)
        specs = [("Qawwali Night", True, Decimal("0")), ("Departmental Seminar", False, Decimal("0")), ("General Workshop", False, Decimal("500"))]
        for title, caspam, price in specs:
            ev = Event.objects.create(title=TAG + title, category=cat, status="published", start_at=when, registration_open=True,
                                      venue="Demo venue", summary="Fictional event for testing registration.")
            cfg = ev.reg_config
            cfg.builtin_enabled, cfg.caspam_verification_enabled, cfg.standard_price = True, caspam, price
            cfg.dataset = ds if caspam else None
            cfg.payment_instructions = "DEMO ONLY — do not send real money."
            cfg.save()
            if price or caspam:
                PaymentMethod.objects.create(config=cfg, kind="easypaisa", title="Easypaisa (demo)", account_title="DEMO", account_number="03000000000")
            if title == "Departmental Seminar":
                RegistrationField.objects.create(config=cfg, key="department", label="Department", required=True, order=1)
                RegistrationField.objects.create(config=cfg, key="semester", label="Semester", required=False, order=2)
        self.stdout.write(self.style.SUCCESS("Created 3 [DEMO] events and a fictional student list (rolls DEMO-001..003)."))
