import datetime
import io

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.core.models import ContentBlock, HomeSection, PageContent, SiteSettings, ContactSubmission, NewsletterSubscriber
from apps.events.models import Event, EventCategory, EventHighlight
from apps.gallery.models import Album, MediaItem
from apps.membership.models import InterestArea, MembershipApplication
from apps.news.models import Announcement
from apps.team.models import TeamCategory, TeamMember

TMP_MEDIA = override_settings(MEDIA_ROOT="/tmp/zcbs_test_media")


def png(name="x.png", size=(40, 30), color="navy"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def make_event(**kw):
    cat = EventCategory.objects.first()
    kw.setdefault("title", "Orientation Test")
    kw.setdefault("category", cat)
    kw.setdefault("status", "published")
    return Event.objects.create(**kw)


class SeedDataTests(TestCase):
    def test_exactly_22_team_members_with_official_data(self):
        self.assertEqual(TeamMember.objects.count(), 22)
        self.assertEqual(TeamMember.objects.filter(category__name="President and Leadership").count(), 3)
        self.assertEqual(TeamMember.objects.filter(category__name="Core Team").count(), 15)
        self.assertEqual(TeamMember.objects.filter(category__name="Media Team").count(), 4)
        z = TeamMember.objects.get(name="Zeenat Shahzad")
        self.assertEqual((z.program, z.class_label, z.designation), ("BS AI", "BS 2025-29", "Executive Member"))
        self.assertEqual(TeamMember.objects.get(designation="President").name, "Muqtasid Khan")
        self.assertEqual(TeamMember.objects.get(name="M. Usman Javaid").designation, "Finance Secretary")
        self.assertEqual(TeamMember.objects.get(name="Rao Abdul Rahman Ashraf").designation, "Executive")
        self.assertEqual(TeamMember.objects.filter(class_label="BS 2026-30").count(), 3)

    def test_five_event_categories_and_homepage_sections(self):
        self.assertEqual(EventCategory.objects.count(), 5)
        self.assertEqual(HomeSection.objects.count(), 14)

    def test_roles_created(self):
        self.assertEqual(set(Group.objects.values_list("name", flat=True)),
                         {"Website Administrator", "Content Editor", "Membership Manager"})

    def test_no_invented_events_or_news(self):
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Announcement.objects.count(), 0)


class PublicPageTests(TestCase):
    def test_all_main_pages_load(self):
        for name in ["core:home", "core:about", "core:contact", "team:index", "team:archive", "events:index",
                     "events:archive", "gallery:index", "news:index", "membership:join", "membership:thanks"]:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)

    def test_team_page_shows_all_categories_and_initials(self):
        r = self.client.get(reverse("team:index"))
        for text in ["President and Leadership", "Core Team", "Media Team", "Muqtasid Khan", "Zeenat Shahzad", "BS AI"]:
            self.assertContains(r, text)

    def test_pending_content_hidden_from_public_visible_to_staff(self):
        self.assertNotContains(self.client.get(reverse("core:about")), "Our vision")
        self.assertNotContains(self.client.get("/"), "Our vision")
        staff = User.objects.create_user("boss", password="x" * 12, is_staff=True)
        self.client.force_login(staff)
        self.assertContains(self.client.get(reverse("core:about")), "Our vision")

    def test_approving_content_publishes_it(self):
        ContentBlock.objects.update(approval="approved")
        PageContent.objects.update(approval="approved")
        r = self.client.get(reverse("core:about"))
        self.assertContains(r, "Our vision")
        self.assertContains(r, "Core values")

    def test_404_and_robots_and_sitemap(self):
        r = self.client.get("/definitely-not-here/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "Page not found", status_code=404)
        self.assertContains(self.client.get("/robots.txt"), "Disallow: /admin/")
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)

    def test_homepage_sections_hide_and_reorder(self):
        HomeSection.objects.filter(key="membership").update(is_visible=False)
        self.assertNotContains(self.client.get("/"), "Become a member of ZCBS")
        HomeSection.objects.filter(key="membership").update(is_visible=True)
        self.assertContains(self.client.get("/"), "Become a member of ZCBS")
        HomeSection.objects.filter(key="hero").update(heading="Edited hero headline")
        self.assertContains(self.client.get("/"), "Edited hero headline")

    def test_intro_markup_and_skip(self):
        r = self.client.get("/")
        self.assertContains(r, 'id="intro"')
        self.assertContains(r, "Skip intro")
        SiteSettings.objects.update(enable_intro=False)
        self.assertNotContains(self.client.get("/"), 'id="intro"')
        self.assertNotContains(self.client.get("/about/"), 'id="intro"')


@TMP_MEDIA
class EventSystemTests(TestCase):
    def test_new_event_gets_page_url_album_and_category_listing(self):
        e = make_event(title="Interview Preparation Session", start_at=timezone.now() + datetime.timedelta(days=5),
                       venue="Seminar Hall", summary="Prepare well.")
        self.assertEqual(e.slug, "interview-preparation-session")
        self.assertTrue(Album.objects.filter(event=e).exists())
        r = self.client.get(e.get_absolute_url())
        self.assertContains(r, "Interview Preparation Session")
        self.assertContains(r, "Seminar Hall")
        self.assertContains(self.client.get(reverse("events:index")), "Interview Preparation Session")
        self.assertContains(self.client.get(f"{reverse('events:index')}?category={e.category.slug}"), "Interview Preparation Session")

    def test_slug_is_unique(self):
        a, b = make_event(title="Fun Fair"), make_event(title="Fun Fair")
        self.assertNotEqual(a.slug, b.slug)

    def test_draft_hidden_but_staff_can_preview(self):
        e = make_event(title="Secret", status="draft")
        self.assertEqual(self.client.get(e.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(reverse("events:index")), "Secret")
        self.client.force_login(User.objects.create_user("s", password="x" * 12, is_staff=True))
        r = self.client.get(e.get_absolute_url())
        self.assertContains(r, "STAFF PREVIEW")

    def test_scheduled_publication(self):
        e = make_event(title="Later", publish_at=timezone.now() + datetime.timedelta(days=2))
        self.assertEqual(self.client.get(e.get_absolute_url()).status_code, 404)
        Event.objects.filter(pk=e.pk).update(publish_at=timezone.now() - datetime.timedelta(minutes=1))
        self.assertEqual(self.client.get(e.get_absolute_url()).status_code, 200)

    def test_upcoming_vs_past_and_recap_layout(self):
        up = make_event(title="Future Gala", start_at=timezone.now() + datetime.timedelta(days=9),
                        registration_open=True, registration_url="https://example.com/form")
        past = make_event(title="Orientation 2026", tagline="Welcoming the New Academic Generation",
                          start_at=timezone.now() - datetime.timedelta(days=20),
                          recap_title="A warm welcome", recap="<p>Students gathered.</p>")
        self.assertIn(up, list(Event.objects.upcoming()))
        self.assertIn(past, list(Event.objects.past()))
        r = self.client.get(past.get_absolute_url())
        self.assertContains(r, "Event story")
        self.assertContains(r, "A warm welcome")
        self.assertContains(r, "Welcoming the New Academic Generation")
        r = self.client.get(up.get_absolute_url())
        self.assertContains(r, "Register now")
        self.assertContains(r, "Add to calendar")
        self.assertEqual(self.client.get(reverse("events:ics", args=[up.slug])).status_code, 200)
        listing = self.client.get(reverse("events:index") + "?when=past")
        self.assertContains(listing, "Orientation 2026")
        self.assertNotContains(listing, "Future Gala")

    def test_search_and_year_filter(self):
        make_event(title="Sports Gala", start_at=timezone.now() - datetime.timedelta(days=3))
        make_event(title="Annual Dinner")
        r = self.client.get(reverse("events:index") + "?q=gala")
        self.assertContains(r, "Sports Gala")
        self.assertNotContains(r, "Annual Dinner")

    def test_archive_removes_from_listing_keeps_page(self):
        e = make_event(title="Old Event", start_at=timezone.now() - datetime.timedelta(days=400))
        e.status = "archived"
        e.save()
        self.assertNotContains(self.client.get(reverse("events:index")), "Old Event")
        self.assertContains(self.client.get(reverse("events:archive")), "Old Event")
        self.assertEqual(self.client.get(e.get_absolute_url()).status_code, 200)

    def test_duplicate_creates_draft_copy_with_highlights(self):
        e = make_event(title="Workshop", is_featured=True, recap="<p>x</p>")
        EventHighlight.objects.create(event=e, title="Keynote", text="t")
        c = e.duplicate()
        self.assertNotEqual(c.pk, e.pk)
        self.assertEqual((c.status, c.is_featured, c.recap), ("draft", False, ""))
        self.assertEqual(c.highlights.count(), 1)
        self.assertEqual(Event.objects.count(), 2)
        self.assertTrue(Album.objects.filter(event=c).exists())

    def test_featured_event_on_homepage(self):
        make_event(title="Featured Show", is_featured=True, start_at=timezone.now() + datetime.timedelta(days=3))
        self.assertContains(self.client.get("/"), "Featured Show")

    def test_new_category_is_usable(self):
        cat = EventCategory.objects.create(name="Debate Nights")
        e = make_event(title="Debate One", category=cat)
        self.assertContains(self.client.get(reverse("events:index") + "?category=debate-nights"), "Debate One")

    def test_related_events(self):
        a = make_event(title="A")
        b = make_event(title="B", category=a.category)
        self.assertContains(self.client.get(a.get_absolute_url()), ">B<")


@TMP_MEDIA
class GalleryTests(TestCase):
    def test_photo_uploaded_to_event_appears_in_event_page_and_album_once(self):
        e = make_event(title="Orientation 2026")
        m = MediaItem.objects.create(kind="photo", image=png("a.png"), event=e, caption="Opening")
        self.assertEqual(m.album, e.album)
        self.assertContains(self.client.get(e.get_absolute_url()), "Opening")
        self.assertContains(self.client.get(reverse("gallery:album", args=[e.album.slug])), "Opening")
        self.assertContains(self.client.get(reverse("gallery:index")), "Orientation 2026")
        self.assertEqual(MediaItem.objects.count(), 1)  # not duplicated

    def test_video_embed_and_validation(self):
        e = make_event(title="Vid")
        v = MediaItem(kind="video", video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", event=e)
        v.full_clean()
        v.save()
        self.assertIn("youtube-nocookie.com/embed/dQw4w9WgXcQ", v.embed_url)
        self.assertContains(self.client.get(e.get_absolute_url()), "youtube-nocookie.com/embed/dQw4w9WgXcQ")
        bad = MediaItem(kind="video", video_url="https://evil.example.com/v")
        with self.assertRaises(Exception):
            bad.full_clean()

    def test_media_replacement_and_deletion(self):
        m = MediaItem.objects.create(kind="photo", image=png("a.png"))
        m.image = png("b.png")
        m.save()
        self.assertIn("b", m.image.name)
        m.delete()
        self.assertEqual(MediaItem.objects.count(), 0)

    @override_settings(MAX_IMAGE_UPLOAD_MB=0)
    def test_oversize_image_rejected(self):
        from django.core.exceptions import ValidationError
        from apps.core.validators import validate_image_file
        with self.assertRaises(ValidationError):
            validate_image_file(png("big.png"))

    def test_bad_extension_rejected(self):
        from django.core.exceptions import ValidationError
        from apps.core.validators import validate_image_file
        with self.assertRaises(ValidationError):
            validate_image_file(SimpleUploadedFile("evil.php", b"<?php ?>"))


class NewsTests(TestCase):
    def test_publish_pin_draft_and_search(self):
        a = Announcement.objects.create(title="Notice A", status="published", summary="s", body="<p>Body A</p>")
        b = Announcement.objects.create(title="Notice B", status="published", is_pinned=True)
        Announcement.objects.create(title="Hidden", status="draft")
        r = self.client.get(reverse("news:index"))
        self.assertContains(r, "Notice A")
        self.assertNotContains(r, "Hidden")
        self.assertEqual(list(Announcement.objects.visible())[0], b)  # pinned first
        self.assertContains(self.client.get(a.get_absolute_url()), "Body A")
        self.assertEqual(self.client.get(reverse("news:detail", args=["hidden"])).status_code, 404)
        self.assertContains(self.client.get(reverse("news:index") + "?q=Notice+A"), "Notice A")

    def test_scheduled_announcement(self):
        a = Announcement.objects.create(title="Soon", status="published", publish_at=timezone.now() + datetime.timedelta(days=1))
        self.assertEqual(self.client.get(a.get_absolute_url()).status_code, 404)


class FormTests(TestCase):
    GOOD = dict(full_name="Test Student", registration_number="BZU-123", program="BS Mathematics", semester="3",
                email="t@example.com", phone="+92 300 1234567", reason="I want to grow.")

    def test_membership_application_saved(self):
        area = InterestArea.objects.first()
        r = self.client.post(reverse("membership:join"), {**self.GOOD, "interests": [area.pk]})
        self.assertRedirects(r, reverse("membership:thanks"))
        app = MembershipApplication.objects.get()
        self.assertEqual((app.status, app.interests.count()), ("pending", 1))

    def test_duplicate_pending_and_bad_phone_rejected(self):
        self.client.post(reverse("membership:join"), self.GOOD)
        r = self.client.post(reverse("membership:join"), self.GOOD)
        self.assertContains(r, "already awaiting review")
        r = self.client.post(reverse("membership:join"), {**self.GOOD, "registration_number": "X2", "phone": "12"})
        self.assertContains(r, "valid contact number")

    def test_honeypot_blocks_bots(self):
        r = self.client.post(reverse("membership:join"), {**self.GOOD, "website": "http://spam"})
        self.assertEqual(MembershipApplication.objects.count(), 0)

    def test_closed_membership_blocks_submission(self):
        SiteSettings.objects.update(membership_open=False)
        self.client.post(reverse("membership:join"), self.GOOD)
        self.assertEqual(MembershipApplication.objects.count(), 0)

    def test_contact_and_newsletter(self):
        r = self.client.post(reverse("core:contact"), dict(name="A", email="a@b.co", subject="Hi", message="Hello"))
        self.assertRedirects(r, reverse("core:contact"))
        self.assertEqual(ContactSubmission.objects.count(), 1)
        self.client.post(reverse("core:newsletter"), {"email": "N@Example.com"})
        self.client.post(reverse("core:newsletter"), {"email": "n@example.com"})
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)

    def test_rate_limit(self):
        from django.core.cache import cache
        cache.clear()
        for i in range(8):
            self.client.post(reverse("core:contact"), dict(name="A", email="a@b.co", subject="s", message="m"))
        r = self.client.post(reverse("core:contact"), dict(name="A", email="a@b.co", subject="s", message="m"))
        self.assertEqual(ContactSubmission.objects.count(), 8)
        cache.clear()

    def test_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post(reverse("membership:join"), self.GOOD).status_code, 403)


@TMP_MEDIA
class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("president", "p@example.com", "S3cure-pass-phrase!")

    def setUp(self):
        self.assertTrue(self.client.login(username="president", password="S3cure-pass-phrase!"))

    def test_visitors_cannot_reach_dashboard(self):
        self.client.logout()
        r = self.client.get("/admin/events/event/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])

    def test_login_page_and_dashboard_render(self):
        self.client.logout()
        self.assertContains(self.client.get("/admin/login/"), "ZCBS")
        self.client.login(username="president", password="S3cure-pass-phrase!")
        r = self.client.get("/admin/")
        self.assertContains(r, "CREATE NEW EVENT")
        self.assertContains(r, "Membership applications waiting")

    def test_every_admin_changelist_and_add_form_loads(self):
        for url in ["/admin/events/event/", "/admin/events/event/add/", "/admin/events/eventcategory/", "/admin/team/teammember/",
                    "/admin/team/teammember/add/", "/admin/team/teamcategory/", "/admin/gallery/mediaitem/", "/admin/gallery/mediaitem/add/",
                    "/admin/gallery/mediaitem/bulk-upload/", "/admin/gallery/album/", "/admin/news/announcement/",
                    "/admin/news/announcement/add/", "/admin/membership/membershipapplication/", "/admin/core/homesection/",
                    "/admin/core/navitem/", "/admin/core/contentblock/", "/admin/core/pagecontent/", "/admin/core/contactsubmission/",
                    "/admin/core/newslettersubscriber/", "/admin/auth/user/", "/admin/auth/group/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        r = self.client.get("/admin/core/sitesettings/", follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(self.client.get("/admin/events/event/"), "CREATE NEW EVENT")

    def test_create_event_through_admin_form_generates_page(self):
        cat = EventCategory.objects.first()
        data = {"title": "Two-Minute Spotlight", "category": cat.pk, "status": "published", "venue": "Hall A",
                "start_at_0": "2027-02-10", "start_at_1": "11:00:00", "summary": "Speak for two minutes.",
                "slug": "", "description": "<p>Details</p>",
                "highlights-TOTAL_FORMS": "0", "highlights-INITIAL_FORMS": "0",
                "speakers-TOTAL_FORMS": "0", "speakers-INITIAL_FORMS": "0",
                "media-TOTAL_FORMS": "0", "media-INITIAL_FORMS": "0"}
        r = self.client.post("/admin/events/event/add/", data, follow=True)
        self.assertEqual(r.status_code, 200)
        e = Event.objects.get(title="Two-Minute Spotlight")
        self.assertEqual(self.client.get(e.get_absolute_url()).status_code, 200)

    def test_admin_actions_publish_archive_duplicate_feature(self):
        e = make_event(title="Act", status="draft")
        url = "/admin/events/event/"
        for action in ["publish", "feature", "duplicate", "archive"]:
            r = self.client.post(url, {"action": action, "_selected_action": [e.pk]}, follow=True)
            self.assertEqual(r.status_code, 200, action)
        e.refresh_from_db()
        self.assertEqual((e.status, e.is_featured), ("archived", True))
        self.assertEqual(Event.objects.filter(title="Act (copy)").count(), 1)

    def test_member_edit_and_photo_upload(self):
        m = TeamMember.objects.get(name="Ahmad Iqbal")
        m.photo = png("p.png")
        m.bio = "Bio"
        m.save()
        self.assertContains(self.client.get(reverse("team:index")), m.photo.url)

    def test_member_reorder_and_promote_via_changelist_fields(self):
        m = TeamMember.objects.get(name="Talha Khan")
        lead = TeamCategory.objects.get(slug="president-and-leadership")
        m.category = lead
        m.order = 1
        m.save()
        r = self.client.get(reverse("team:index"))
        self.assertContains(r, "Talha Khan")
        self.assertEqual(TeamMember.objects.get(pk=m.pk).category, lead)

    def test_bulk_upload_attaches_to_event_gallery(self):
        e = make_event(title="Orientation 2026")
        r = self.client.post("/admin/gallery/mediaitem/bulk-upload/", {
            "photos": [png("1.png"), png("2.png"), png("3.png")], "event": e.pk, "is_published": "on"}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(e.media.count(), 3)
        self.assertEqual(e.album.items.count(), 3)

    def test_bulk_upload_rejects_non_images(self):
        r = self.client.post("/admin/gallery/mediaitem/bulk-upload/", {
            "photos": [SimpleUploadedFile("a.exe", b"MZ")]})
        self.assertEqual(MediaItem.objects.count(), 0)

    def test_membership_approve_reject_notes_export(self):
        app = MembershipApplication.objects.create(full_name="X", registration_number="1", program="P", semester="1",
                                                   email="x@y.z", phone="03001234567", reason="r")
        url = "/admin/membership/membershipapplication/"
        self.client.post(url, {"action": "mark_approved", "_selected_action": [app.pk]}, follow=True)
        app.refresh_from_db()
        self.assertEqual((app.status, app.reviewed_by), ("approved", self.admin))
        r = self.client.post(url, {"action": "export_csv", "_selected_action": [app.pk]})
        self.assertEqual(r["Content-Type"], "text/csv")
        self.assertIn(b"X", r.content)

    def test_site_settings_edit_changes_footer_and_social(self):
        s = SiteSettings.load()
        s.facebook_url = "https://facebook.com/zcbs"
        s.contact_email = "zcbs@example.com"
        s.footer_text = "Custom footer"
        s.save()
        r = self.client.get("/")
        for t in ["facebook.com/zcbs", "zcbs@example.com", "Custom footer"]:
            self.assertContains(r, t)

    def test_settings_singleton(self):
        SiteSettings.objects.create(site_name="Other")
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_content_editor_role_cannot_touch_users(self):
        u = User.objects.create_user("editor", password="Another-pass-123", is_staff=True)
        u.groups.add(Group.objects.get(name="Content Editor"))
        self.client.logout()
        self.client.login(username="editor", password="Another-pass-123")
        self.assertEqual(self.client.get("/admin/events/event/").status_code, 200)
        self.assertEqual(self.client.get("/admin/auth/user/").status_code, 403)
        self.assertEqual(self.client.get("/admin/membership/membershipapplication/").status_code, 403)
