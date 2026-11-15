import datetime
import re

from django.test import TestCase
from django.utils import timezone

from apps.core.models import ContentBlock, PageContent
from apps.events.models import Event, EventCategory
from apps.news.models import Announcement


class LinkCrawlTest(TestCase):
    """Follows every internal link reachable from the homepage and requires each to load."""

    def test_no_broken_internal_links(self):
        ContentBlock.objects.update(approval="approved")
        PageContent.objects.update(approval="approved")
        cat = EventCategory.objects.first()
        Event.objects.create(title="Past One", category=cat, status="published", recap="<p>r</p>",
                             start_at=timezone.now() - datetime.timedelta(days=9))
        Event.objects.create(title="Next One", category=cat, status="published", is_featured=True,
                             start_at=timezone.now() + datetime.timedelta(days=9))
        Announcement.objects.create(title="Hello", status="published")
        seen, queue, bad = set(), ["/"], []
        while queue:
            url = queue.pop()
            if url in seen:
                continue
            seen.add(url)
            r = self.client.get(url)
            if r.status_code != 200:
                bad.append((url, r.status_code))
                continue
            if "text/html" not in r["Content-Type"]:
                continue
            for href in re.findall(r'href="([^"#]+)"', r.content.decode()):
                if href.startswith("/") and not href.startswith(("/static/", "/media/", "/admin/", "//")):
                    queue.append(href)
        self.assertEqual(bad, [])
        self.assertGreater(len(seen), 15)
