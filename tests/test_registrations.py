"""Event registration system tests. ALL data below is fictional."""
import io
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.events.models import Event, EventCategory
from apps.registrations import services
from apps.registrations.models import AuditLog, AuthorizedStudent, EventRegistrationConfig, PaymentMethod, Registration, RegistrationField, StudentDataset

CSV = ("Roll No,Student Name,CNIC,WhatsApp\n"
       "TEST-001,Aisha Test Khan,3520111111111,0300 1234567\n"
       "TEST-002,Bilal Test Ahmed,3520222222222,0301-7654321\n"
       "TEST-003,Carol Test Noor,,\n")


def make_dataset(active=True):
    ds = StudentDataset.objects.create(name="FICTIONAL TEST DATA", is_test_data=True, is_active=active)
    services.import_dataset(ds, SimpleUploadedFile("t.csv", CSV.encode()))
    return ds


def make_event(title="Test Event", caspam=False, ds=None, **cfg_kw):
    ev = Event.objects.create(title=title, category=EventCategory.objects.first(), status="published",
                              start_at=timezone.now() + timezone.timedelta(days=10), registration_open=True)
    cfg = ev.reg_config
    cfg.builtin_enabled = True
    cfg.caspam_verification_enabled = caspam
    cfg.dataset = ds
    for k, v in cfg_kw.items():
        setattr(cfg, k, v)
    cfg.save()
    PaymentMethod.objects.create(config=cfg, kind="easypaisa", title="Easypaisa", account_number="03000000000")
    return ev


def post_reg(client, ev, **data):
    base = {"full_name": "Aisha Test Khan", "email": "aisha@example.test", "phone": "03001234567"}
    base.update(data)
    return client.post(reverse("registrations:register", args=[ev.slug]), base)


def user_with_role(name, role, staff=True):
    u = User.objects.create_user(name, password="x-Strong-pass-1", is_staff=staff)
    u.groups.add(Group.objects.get(name=role))
    return u


class Base(TestCase):
    def setUp(self):
        cache.clear()


class ScenarioA_CaspamOn(Base):
    def setUp(self):
        super().setUp()
        self.ds = make_dataset()
        self.ev = make_event("Qawwali Night (TEST)", caspam=True, ds=self.ds,
                             caspam_price=1500, external_price=2000)

    def caspam(self, **kw):
        d = {"participant_type": "caspam", "caspam_roll": "test-001", "second_factor": "0300-1234567"}
        d.update(kw)
        return post_reg(self.client, self.ev, **d)

    def test_verified_student_gets_1500(self):
        r = self.caspam()
        reg = Registration.objects.get()
        self.assertRedirects(r, reverse("registrations:mine", args=[reg.access_token]))
        self.assertEqual((reg.verification_status, reg.category, reg.price), ("verified", "caspam", Decimal("1500")))

    def test_external_gets_2000_and_needs_no_roll(self):
        post_reg(self.client, self.ev, participant_type="external", email="ext@example.test")
        reg = Registration.objects.get()
        self.assertEqual((reg.category, reg.price, reg.verification_status), ("external", Decimal("2000"), "not_required"))

    def test_invalid_roll_gets_no_discount(self):
        self.caspam(caspam_roll="NOPE-999")
        reg = Registration.objects.get()
        self.assertEqual((reg.verification_status, reg.category, reg.price, reg.caspam_roll), ("not_verified", "external", Decimal("2000"), ""))

    def test_name_alone_never_verifies(self):
        # correct name + phone of a real student but a roll number that is not in the list
        self.caspam(caspam_roll="TEST-777")
        self.assertEqual(Registration.objects.get().price, Decimal("2000"))

    def test_conflicting_details_go_to_manual_review(self):
        self.caspam(second_factor="0399-9999999")          # real roll + name, wrong mobile
        reg = Registration.objects.get()
        self.assertEqual((reg.verification_status, reg.category, reg.price), ("pending_review", "external", Decimal("2000")))
        self.assertIn("mobile", reg.verification_note)

    def test_wrong_name_with_real_roll_goes_to_review(self):
        self.caspam(full_name="Zed Totally Different")
        self.assertEqual(Registration.objects.get().verification_status, "pending_review")

    def test_roll_required_when_claiming_caspam(self):
        r = self.caspam(caspam_roll="")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Registration.objects.count(), 0)

    def test_frontend_price_is_ignored(self):
        self.caspam(price="1", amount="1", ticket_price="1", caspam_roll="BAD")
        self.assertEqual(Registration.objects.get().price, Decimal("2000"))

    def test_forging_caspam_category_without_verification_is_impossible(self):
        post_reg(self.client, self.ev, participant_type="external", category="caspam", email="x@example.test")
        self.assertEqual(Registration.objects.get().price, Decimal("2000"))

    def test_manual_review_approve_applies_discount_and_reject_does_not(self):
        self.caspam(second_factor="0399-9999999")
        reg = Registration.objects.get()
        mgr = user_with_role("mgr", "Event Manager")
        services.resolve_verification(reg, True, mgr)
        reg.refresh_from_db()
        self.assertEqual((reg.verification_status, reg.price), ("verified", Decimal("1500")))
        post_reg(self.client, self.ev, email="b@example.test", full_name="Bilal Test Ahmed", participant_type="caspam",
                 caspam_roll="TEST-002", second_factor="0300-0000000")
        r2 = Registration.objects.get(email="b@example.test")
        services.resolve_verification(r2, False, mgr)
        r2.refresh_from_db()
        self.assertEqual((r2.verification_status, r2.price), ("not_verified", Decimal("2000")))

    def test_duplicate_roll_rejected(self):
        self.caspam()
        r = self.caspam(email="other@example.test")
        self.assertEqual(Registration.objects.count(), 1)
        self.assertContains(r, "already registered")

    def test_payment_blocked_while_review_pending(self):
        self.caspam(second_factor="0399-9999999")
        reg = Registration.objects.get()
        with self.assertRaises(services.RegistrationError):
            services.submit_payment(reg, reg.event.reg_config.payment_methods.first(), "TXN12345")

    def test_payment_workflow_and_pass_activation(self):
        self.caspam()
        reg = Registration.objects.get()
        self.assertEqual(reg.pass_status, "inactive")
        m = self.ev.reg_config.payment_methods.first()
        self.client.post(reverse("registrations:mine", args=[reg.access_token]),
                         {"action": "payment", "method": m.pk, "reference": "EP-TXN-001"})
        reg.refresh_from_db()
        self.assertEqual(reg.payment_status, "payment_submitted")
        self.assertEqual(reg.pass_status, "inactive")                 # submitting is not paying
        fin = user_with_role("fin", "Finance Manager")
        services.change_payment(reg, "under_review", fin)
        services.change_payment(reg, "paid", fin)
        reg.refresh_from_db()
        self.assertEqual(reg.pass_status, "active")
        page = self.client.get(reverse("registrations:mine", args=[reg.access_token]))
        self.assertContains(page, reg.verification_code)

    def test_illegal_payment_jumps_refused(self):
        self.caspam()
        reg = Registration.objects.get()
        with self.assertRaises(ValueError):
            reg.set_payment_status("refunded")      # unpaid -> refunded
        with self.assertRaises(ValueError):
            reg.set_payment_status("under_review")  # unpaid -> under review

    def test_reject_then_resubmit(self):
        self.caspam()
        reg = Registration.objects.get()
        fin = user_with_role("fin", "Finance Manager")
        m = self.ev.reg_config.payment_methods.first()
        services.submit_payment(reg, m, "TXN-AAAA")
        services.change_payment(reg, "rejected", fin)
        services.submit_payment(reg, m, "TXN-BBBB")
        self.assertEqual(reg.payment_status, "payment_submitted")

    def test_pass_page_has_no_downloads_no_qr_no_personal_data_in_url(self):
        self.caspam()
        reg = Registration.objects.get()
        reg.payment_status = "paid"
        reg.save()
        url = reverse("registrations:mine", args=[reg.access_token])
        for secret in (reg.email, reg.full_name.split()[0].lower(), "aisha", reg.phone):
            self.assertNotIn(secret, url.lower())
        r = self.client.get(url)
        self.assertIn("no-store", r["Cache-Control"])
        html = r.content.decode().lower()
        for bad in ("<canvas", "qrcode", "qr code", "download=", "application/pdf", ".pdf"):
            self.assertNotIn(bad, html)
        self.assertIn("noindex", r["X-Robots-Tag"])

    # ---- entry ----
    def paid_reg(self, **kw):
        self.caspam(**kw)
        reg = Registration.objects.order_by("-id").first()
        reg.payment_status = "paid"
        reg.save()
        return reg

    def test_checkin_once_only(self):
        reg = self.paid_reg()
        staff = user_with_role("door", "Check-in Staff")
        ok, msg, _ = services.check_in(reg.verification_code.lower(), staff, self.ev)
        self.assertTrue(ok)
        reg.refresh_from_db()
        self.assertEqual((reg.pass_status, reg.checked_in_by), ("used", staff))
        ok2, msg2, _ = services.check_in(reg.verification_code, staff, self.ev)
        self.assertFalse(ok2)
        self.assertIn("ALREADY USED", msg2)

    def test_checkin_uses_one_conditional_update(self):
        """The winner is decided by a single UPDATE ... WHERE checked_in_at IS NULL, so a stale view of the row cannot double-admit."""
        reg = self.paid_reg()
        staff = user_with_role("door", "Check-in Staff")
        stale = Registration.objects.get(pk=reg.pk)
        self.assertTrue(services.check_in(reg.verification_code, staff, self.ev)[0])
        n = Registration.objects.filter(pk=stale.pk, checked_in_at__isnull=True).update(checked_in_at=timezone.now())
        self.assertEqual(n, 0)
        self.assertEqual(AuditLog.objects.filter(action="checkin_ok").count(), 1)

    def test_checkin_denied_cases(self):
        staff = user_with_role("door", "Check-in Staff")
        self.assertFalse(services.check_in("ZZZZZ-ZZZZZ", staff, self.ev)[0])        # unknown
        self.caspam()
        unpaid = Registration.objects.get()
        self.assertFalse(services.check_in(unpaid.verification_code, staff, self.ev)[0])   # payment not confirmed
        unpaid.payment_status = "paid"
        unpaid.save()
        services.set_pass_revoked(unpaid, True, staff, reason="test")
        ok, msg, _ = services.check_in(unpaid.verification_code, staff, self.ev)
        self.assertFalse(ok)
        self.assertIn("revoked", msg)
        services.set_pass_revoked(unpaid, False, staff)
        other = make_event("Other Event")
        self.assertFalse(services.check_in(unpaid.verification_code, staff, other)[0])      # wrong event
        self.assertTrue(services.check_in(unpaid.verification_code, staff, self.ev)[0])

    def test_pending_review_cannot_enter(self):
        reg = self.paid_reg(second_factor="0399-9999999")
        staff = user_with_role("door", "Check-in Staff")
        self.assertFalse(services.check_in(reg.verification_code, staff, self.ev)[0])

    def test_checkin_screen_permissions_and_flow(self):
        reg = self.paid_reg()
        c = self.client
        self.assertEqual(c.get(reverse("registrations:checkin")).status_code, 302)          # anonymous -> login
        fin = user_with_role("fin", "Finance Manager")
        c.force_login(fin)
        self.assertEqual(c.get(reverse("registrations:checkin")).status_code, 403)          # wrong role
        c.force_login(user_with_role("door", "Check-in Staff"))
        r = c.post(reverse("registrations:checkin"), {"code": reg.verification_code, "event": self.ev.pk, "do": "lookup"})
        self.assertContains(r, "ADMIT")
        r = c.post(reverse("registrations:checkin"), {"code": reg.verification_code, "event": self.ev.pk, "do": "admit"})
        self.assertContains(r, "Entry confirmed")
        r = c.post(reverse("registrations:checkin"), {"code": reg.verification_code, "event": self.ev.pk, "do": "admit"})
        self.assertContains(r, "ALREADY USED")

    def test_live_status_endpoint_flips_when_used(self):
        reg = self.paid_reg()
        url = reverse("registrations:pass_status", args=[reg.access_token])
        self.assertEqual(self.client.get(url).json(), {"status": "active"})
        services.check_in(reg.verification_code, user_with_role("door", "Check-in Staff"), self.ev)
        self.assertEqual(self.client.get(url).json(), {"status": "used"})

    def test_lookup_requires_matching_email(self):
        self.caspam()
        reg = Registration.objects.get()
        r = self.client.post(reverse("registrations:lookup"), {"reference": reg.reference, "email": "wrong@example.test"})
        self.assertContains(r, "could not find")
        r = self.client.post(reverse("registrations:lookup"), {"reference": reg.reference, "email": "AISHA@example.test"})
        self.assertRedirects(r, reverse("registrations:mine", args=[reg.access_token]))

    def test_cnic_is_never_stored(self):
        ev = make_event("CNIC Event", caspam=True, ds=self.ds, second_factor="cnic")
        post_reg(self.client, ev, participant_type="caspam", caspam_roll="TEST-001", second_factor="35201-1111111-1")
        reg = Registration.objects.get(event=ev)
        self.assertEqual(reg.verification_status, "verified")
        blob = " ".join(str(v) for v in reg.__dict__.values()) + str(AuthorizedStudent.objects.values())
        self.assertNotIn("3520111111111", blob)
        self.assertNotIn("1234567", str(list(AuthorizedStudent.objects.values_list("phone_hash", flat=True))))


class ScenarioB_CaspamOff(Base):
    def setUp(self):
        super().setUp()
        self.ev = make_event("Departmental Seminar (TEST)", caspam=False, standard_price=Decimal("500"))

    def test_form_has_no_caspam_fields(self):
        r = self.client.get(reverse("registrations:register", args=[self.ev.slug]))
        page = r.content.decode().lower()
        form = page[page.index('id="reg-form"'):page.index("</form>", page.index('id="reg-form"'))]
        for word in ("caspam", "roll", "participant_type", "second_factor"):
            self.assertNotIn(word, form)
        self.assertNotIn("participant_type", page)          # not even the toggle script is sent

    def test_registers_without_roll_and_normal_price_applies(self):
        with mock.patch("apps.registrations.services.verify_caspam", side_effect=AssertionError("dataset matching must not run")):
            post_reg(self.client, self.ev, participant_type="caspam", caspam_roll="TEST-001")   # junk CASPAM input is ignored
        reg = Registration.objects.get()
        self.assertEqual((reg.category, reg.verification_status, reg.price, reg.caspam_roll), ("general", "not_required", Decimal("500"), ""))

    def test_free_event_pass_active_immediately(self):
        cfg = self.ev.reg_config
        cfg.standard_price = 0
        cfg.save()
        post_reg(self.client, self.ev)
        reg = Registration.objects.get()
        self.assertEqual((reg.payment_status, reg.pass_status), ("not_required", "active"))

    def test_custom_fields_required_optional_and_stored(self):
        cfg = self.ev.reg_config
        RegistrationField.objects.create(config=cfg, key="department", label="Department", required=True)
        RegistrationField.objects.create(config=cfg, key="diet", label="Dietary needs", required=False)
        self.assertEqual(post_reg(self.client, self.ev).status_code, 200)       # missing required -> form again
        self.assertEqual(Registration.objects.count(), 0)
        post_reg(self.client, self.ev, f_department="Mathematics")
        self.assertEqual(Registration.objects.get().answers["department"]["value"], "Mathematics")

    def test_phone_can_be_hidden(self):
        cfg = self.ev.reg_config
        cfg.phone_mode = "hidden"
        cfg.save()
        self.assertNotIn("Contact number", self.client.get(reverse("registrations:register", args=[self.ev.slug])).content.decode())
        r = self.client.post(reverse("registrations:register", args=[self.ev.slug]), {"full_name": "No Phone Person", "email": "np@example.test"})
        self.assertEqual(r.status_code, 302)

    def test_cnic_cannot_be_added_as_ordinary_field(self):
        from django.core.exceptions import ValidationError
        f = RegistrationField(config=self.ev.reg_config, key="cnic_number", label="CNIC")
        with self.assertRaises(ValidationError):
            f.full_clean()

    def test_capacity_enforced(self):
        cfg = self.ev.reg_config
        cfg.capacity = 1
        cfg.save()
        post_reg(self.client, self.ev)
        r = post_reg(self.client, self.ev, email="two@example.test")
        self.assertContains(r, "capacity")
        self.assertEqual(Registration.objects.count(), 1)

    def test_closed_registration_refused(self):
        self.ev.registration_deadline = timezone.now() - timezone.timedelta(days=1)
        self.ev.save()
        post_reg(self.client, self.ev)
        self.assertEqual(Registration.objects.count(), 0)

    def test_honeypot_and_rate_limit(self):
        post_reg(self.client, self.ev, website="http://spam.test")
        self.assertEqual(Registration.objects.count(), 0)
        cache.clear()
        for i in range(15):
            post_reg(self.client, self.ev, full_name="", email=f"s{i}@example.test")
        r = post_reg(self.client, self.ev, email="late@example.test")
        self.assertContains(r, "Too many attempts")
        self.assertEqual(Registration.objects.count(), 0)


class ScenarioC_MultipleEvents(Base):
    def test_settings_are_independent_per_event(self):
        ds = make_dataset()
        a = make_event("Qawwali Night (TEST)", caspam=True, ds=ds)
        b = make_event("Seminar (TEST)", caspam=False)
        c = make_event("Gala (TEST)", caspam=False)
        c_cfg = c.reg_config
        c_cfg.caspam_verification_enabled, c_cfg.dataset = True, ds
        c_cfg.external_price = 3000
        c_cfg.save()
        for ev in (a, b, c):
            ev.reg_config.refresh_from_db()
        self.assertEqual([e.reg_config.caspam_verification_enabled for e in (a, b, c)], [True, False, True])
        c_cfg.caspam_verification_enabled = False
        c_cfg.save()
        a.reg_config.refresh_from_db(); b.reg_config.refresh_from_db()
        self.assertTrue(a.reg_config.caspam_verification_enabled)
        self.assertFalse(b.reg_config.caspam_verification_enabled)
        self.assertEqual(a.reg_config.external_price, 2000)

    def test_registration_data_stays_with_its_event(self):
        ds = make_dataset()
        a = make_event("A (TEST)", caspam=True, ds=ds)
        b = make_event("B (TEST)", caspam=False)
        post_reg(self.client, a, participant_type="caspam", caspam_roll="TEST-001", second_factor="03001234567")
        post_reg(self.client, b)                       # same person, different event: allowed
        self.assertEqual(a.registrations.count(), 1)
        self.assertEqual(b.registrations.count(), 1)
        self.assertEqual(a.registrations.get().price, 1500)
        self.assertEqual(b.registrations.get().price, 0)

    def test_new_event_gets_registration_system_automatically(self):
        ev = Event.objects.create(title="Brand new", category=EventCategory.objects.first(), status="published")
        self.assertTrue(EventRegistrationConfig.objects.filter(event=ev).exists())
        self.assertFalse(ev.reg_config.caspam_verification_enabled)   # never ON by default
        self.assertTrue(ev.reg_config.builtin_enabled)

    def test_new_event_with_external_link_keeps_link(self):
        ev = Event.objects.create(title="Linked", category=EventCategory.objects.first(), status="published",
                                  registration_open=True, registration_url="https://forms.example.test/x")
        self.assertFalse(ev.reg_config.builtin_enabled)
        page = self.client.get(ev.get_absolute_url())
        self.assertContains(page, "https://forms.example.test/x")

    def test_existing_events_migrate_without_changing_behaviour(self):
        import importlib
        mig = importlib.import_module("apps.registrations.migrations.0002_attach_existing_events")
        old = Event.objects.create(title="Old event", category=EventCategory.objects.first(), status="published",
                                   registration_open=True, registration_url="https://forms.example.test/old",
                                   registration_info="<p>Use the form</p>")
        EventRegistrationConfig.objects.filter(event=old).delete()
        from django.apps import apps as global_apps
        mig.attach(global_apps, None)
        cfg = EventRegistrationConfig.objects.get(event=old)
        self.assertFalse(cfg.builtin_enabled)
        page = self.client.get(old.get_absolute_url())
        self.assertContains(page, "https://forms.example.test/old")
        self.assertNotContains(page, reverse("registrations:register", args=[old.slug]))
        # the admin can then switch the new system on for this very event
        cfg.builtin_enabled = True
        cfg.save()
        self.assertContains(self.client.get(old.get_absolute_url()), reverse("registrations:register", args=[old.slug]))

    def test_duplicate_event_copy_gets_fresh_settings(self):
        ev = make_event("Dup (TEST)", caspam=False)
        copy = ev.duplicate()
        self.assertTrue(EventRegistrationConfig.objects.filter(event=copy).exists())
        self.assertEqual(copy.registrations.count(), 0)

    def test_event_with_registrations_cannot_be_deleted_silently(self):
        from django.db.models import ProtectedError
        ev = make_event("Prot (TEST)")
        post_reg(self.client, ev)
        with self.assertRaises(ProtectedError):
            ev.delete()


class DatasetAndSecurity(Base):
    def test_import_hashes_sensitive_values_and_masks(self):
        ds = make_dataset()
        s = ds.students.get(roll_norm="TEST001")
        self.assertEqual(len(s.cnic_hash), 64)
        self.assertEqual(s.cnic_last4, "1111")
        dump = str(list(AuthorizedStudent.objects.values()))
        self.assertNotIn("3520111111111", dump)
        self.assertNotIn("03001234567", dump)
        self.assertEqual(ds.row_count, 3)

    def test_bad_uploads_rejected(self):
        ds = StudentDataset.objects.create(name="x")
        for name, body in (("a.exe", b"MZ"), ("a.xlsx", b"not a zip"), ("a.csv", b"foo,bar\n1,2\n"), ("a.csv", b"Roll,Name\n")):
            with self.assertRaises(ValueError, msg=name):
                services.import_dataset(ds, SimpleUploadedFile(name, body))

    def test_xlsx_dataset_supported(self):
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active
        ws.append(["Roll Number", "Name", "Mobile"]); ws.append(["X-1", "Test Person", "0300 1112223"])
        buf = io.BytesIO(); wb.save(buf)
        ds = StudentDataset.objects.create(name="xl")
        res = services.import_dataset(ds, SimpleUploadedFile("d.xlsx", buf.getvalue()))
        self.assertEqual(res["imported"], 1)

    def test_inactive_or_missing_dataset_sends_to_review_not_discount(self):
        ev = make_event("NoDS", caspam=True, ds=None)
        post_reg(self.client, ev, participant_type="caspam", caspam_roll="TEST-001", second_factor="03001234567")
        reg = Registration.objects.get()
        self.assertEqual((reg.verification_status, reg.price), ("pending_review", Decimal("2000")))

    def test_caspam_on_requires_dataset_in_admin_validation(self):
        from django.core.exceptions import ValidationError
        ev = make_event("V", caspam=False)
        cfg = ev.reg_config
        cfg.caspam_verification_enabled = True
        with self.assertRaises(ValidationError):
            cfg.full_clean()

    def test_roles_have_exact_permissions(self):
        def perms(role):
            return set(Group.objects.get(name=role).permissions.values_list("codename", flat=True))
        self.assertEqual(perms("Check-in Staff"), {"perform_checkin"})
        fin = perms("Finance Manager")
        self.assertIn("approve_payment", fin)
        for no in ("verify_student", "upload_dataset", "perform_checkin", "manage_pass", "change_eventregistrationconfig"):
            self.assertNotIn(no, fin)
        em = perms("Event Manager")
        self.assertIn("verify_student", em)
        self.assertNotIn("approve_payment", em)
        self.assertNotIn("perform_checkin", em)
        sa = perms("Super Admin")
        self.assertTrue({"approve_payment", "verify_student", "perform_checkin", "view_auditlog"} <= sa)

    def test_staff_pages_require_login_and_permission(self):
        ev = make_event("E")
        urls = [reverse("registrations:dashboard"), reverse("registrations:checkin"), reverse("registrations:export", args=[ev.pk, "all"])]
        for u in urls:
            self.assertEqual(self.client.get(u).status_code, 302, u)
        self.client.force_login(user_with_role("door", "Check-in Staff"))
        for u in (urls[0], urls[2]):
            self.assertEqual(self.client.get(u).status_code, 403, u)
        self.client.force_login(user_with_role("fin", "Finance Manager"))
        self.assertEqual(self.client.get(urls[0]).status_code, 200)
        self.assertEqual(self.client.get(urls[1]).status_code, 403)

    def test_admin_actions_respect_roles(self):
        ev = make_event("Adm")
        post_reg(self.client, ev, participant_type="x") if False else None
        ev.reg_config.standard_price = 500
        ev.reg_config.save()
        post_reg(self.client, ev)
        reg = Registration.objects.get()
        services.submit_payment(reg, ev.reg_config.payment_methods.first(), "TXN-1111")
        url = reverse("admin:registrations_registration_changelist")
        # Event Manager must NOT be able to approve payments (action not offered / refused)
        self.client.force_login(user_with_role("em", "Event Manager"))
        self.client.post(url, {"action": "act_payment_paid", "_selected_action": [reg.pk]})
        reg.refresh_from_db()
        self.assertEqual(reg.payment_status, "payment_submitted")
        self.client.force_login(user_with_role("fin", "Finance Manager"))
        self.client.post(url, {"action": "act_payment_paid", "_selected_action": [reg.pk]}, follow=True)
        reg.refresh_from_db()
        self.assertEqual(reg.payment_status, "paid")
        self.assertTrue(AuditLog.objects.filter(action="payment_paid", registration=reg).exists())
        # Finance cannot revoke passes
        self.client.post(url, {"action": "act_revoke", "_selected_action": [reg.pk]})
        reg.refresh_from_db()
        self.assertFalse(reg.pass_revoked)

    def test_registration_records_are_read_only_in_admin(self):
        ev = make_event("RO")
        post_reg(self.client, ev)
        reg = Registration.objects.get()
        su = User.objects.create_superuser("root", "r@example.test", "x-Strong-pass-1")
        self.client.force_login(su)
        self.client.post(reverse("admin:registrations_registration_change", args=[reg.pk]), {"price": "1"})
        reg.refresh_from_db()
        self.assertEqual(reg.price, 0)
        self.assertEqual(self.client.get(reverse("admin:registrations_registration_add")).status_code, 403)

    def test_dataset_upload_through_admin_and_masked_listing(self):
        self.client.force_login(user_with_role("em", "Event Manager"))
        r = self.client.post(reverse("admin:registrations_studentdataset_add"),
                             {"name": "Admin upload (TEST)", "is_test_data": "on", "is_active": "on",
                              "upload": SimpleUploadedFile("d.csv", CSV.encode())}, follow=True)
        self.assertEqual(StudentDataset.objects.get().row_count, 3)
        lst = self.client.get(reverse("admin:registrations_authorizedstudent_changelist")).content.decode()
        self.assertNotIn("Aisha", lst)
        self.assertNotIn("3520111111111", lst)
        self.assertIn("TEST-001", lst)

    def test_export_workbook(self):
        ds = make_dataset()
        ev = make_event("Export (TEST)", caspam=True, ds=ds)
        post_reg(self.client, ev, participant_type="caspam", caspam_roll="TEST-001", second_factor="03001234567")
        post_reg(self.client, ev, participant_type="external", full_name="=HYPERLINK(\"http://evil\")", email="e@example.test")
        post_reg(self.client, ev, participant_type="caspam", full_name="Bilal Test Ahmed", email="b@example.test",
                 caspam_roll="TEST-002", second_factor="03999999999")
        self.client.force_login(user_with_role("fin", "Finance Manager"))
        got = {}
        for kind in ("all", "caspam", "external", "paid", "pending", "checked_in"):
            r = self.client.get(reverse("registrations:export", args=[ev.pk, kind]))
            self.assertEqual(r.status_code, 200, kind)
            self.assertIn("spreadsheetml", r["Content-Type"])
            ws = load_workbook(io.BytesIO(r.content)).active
            got[kind] = (ws, ws.max_row - 4)
        self.assertEqual([got[k][1] for k in ("all", "caspam", "external", "paid", "pending", "checked_in")], [3, 1, 2, 0, 3, 0])
        ws = got["all"][0]
        self.assertEqual(ws.freeze_panes, "C5")
        self.assertTrue(ws.auto_filter.ref.startswith("A4"))
        self.assertTrue(ws["A4"].font.bold)
        self.assertGreater(ws.column_dimensions["B"].width, 12)
        text = " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)
        self.assertNotIn("3520111111111", text)
        self.assertNotIn("CNIC", text.replace("CNIC numbers are never stored or exported", ""))
        self.assertTrue(any(str(c.value).startswith("'=HYPERLINK") for row in ws.iter_rows() for c in row if c.value))
        header = [c.value for c in ws[4]]
        self.assertIn("Payment status", header)
        self.assertIn("Roll number (matched)", header)

    def test_export_for_caspam_off_event_has_no_roll_column(self):
        ev = make_event("Off")
        post_reg(self.client, ev)
        self.client.force_login(user_with_role("fin", "Finance Manager"))
        ws = load_workbook(io.BytesIO(self.client.get(reverse("registrations:export", args=[ev.pk, "all"])).content)).active
        self.assertNotIn("Roll number (matched)", [c.value for c in ws[4]])
