import re

from django.test import TestCase, override_settings

from apps.core.models import ContentBlock, PageContent

BASE = "https://zcbscaspamchapter.vercel.app"
PAGES = ["/", "/about/", "/team/", "/events/", "/gallery/", "/news/", "/join/", "/contact/"]


def meta(html, pattern):
    m = re.search(pattern, html)
    return m.group(1) if m else None


@override_settings(SITE_URL=BASE)
class SeoTest(TestCase):
    def setUp(self):
        ContentBlock.objects.update(approval="approved")
        PageContent.objects.update(approval="approved")

    def get(self, url):
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, url)
        return r.content.decode()

    def test_canonical_uses_one_public_address_and_drops_query(self):
        html = self.get("/about/?utm=x&ref=y")
        self.assertEqual(meta(html, r'<link rel="canonical" href="([^"]+)"'), BASE + "/about/")
        self.assertEqual(meta(html, r'property="og:url" content="([^"]+)"'), BASE + "/about/")

    def test_titles_and_descriptions_are_unique(self):
        titles, descs = {}, {}
        for u in PAGES:
            html = self.get(u)
            t = meta(html, r"<title>(.*?)</title>")
            d = meta(html, r'<meta name="description" content="([^"]*)"')
            self.assertTrue(t and d, u)
            self.assertNotIn(t, titles, f"{u} repeats the title of {titles.get(t)}")
            self.assertNotIn(d, descs, f"{u} repeats the description of {descs.get(d)}")
            titles[t], descs[d] = u, u

    def test_one_h1_and_og_matches_page(self):
        for u in PAGES:
            html = self.get(u)
            self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1, u)
        html = self.get("/gallery/")
        self.assertEqual(meta(html, r"<title>(.*?)</title>"), meta(html, r'property="og:title" content="([^"]+)"'))

    def test_og_image_is_absolute_and_not_doubled(self):
        html = self.get("/")
        img = meta(html, r'property="og:image" content="([^"]+)"')
        self.assertTrue(img.startswith(BASE + "/static/"), img)
        self.assertEqual(img.count("http"), 1)

    def test_robots_and_sitemap(self):
        r = self.client.get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        txt = r.content.decode()
        self.assertIn("Disallow: /admin/", txt)
        self.assertIn(f"Sitemap: {BASE}/sitemap.xml", txt)
        self.assertNotIn("Disallow: /\n", txt)
        sm = self.client.get("/sitemap.xml").content.decode()
        self.assertNotIn("/admin/", sm)
        self.assertIn("<loc>", sm)

    def test_no_public_page_is_noindex_but_thanks_is(self):
        for u in PAGES:
            self.assertNotIn("noindex", self.get(u), u)
        self.assertIn('content="noindex"', self.get("/join/thank-you/"))

    def test_jsonld_uses_public_address(self):
        html = self.get("/")
        self.assertIn(BASE + "/#organization", html)

    def test_favicon_ico_redirects(self):
        r = self.client.get("/favicon.ico")
        self.assertIn(r.status_code, (301, 302))

    def test_404_has_status_404(self):
        self.assertEqual(self.client.get("/does-not-exist/").status_code, 404)
