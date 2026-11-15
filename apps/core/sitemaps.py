from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.events.models import Event
from apps.gallery.models import Album
from apps.news.models import Announcement


class StaticSitemap(Sitemap):
    priority, changefreq = 0.8, "monthly"

    def items(self):
        return ["core:home", "core:about", "team:index", "events:index", "gallery:index", "news:index",
                "membership:join", "core:contact"]

    def location(self, item):
        return reverse(item)


class EventSitemap(Sitemap):
    priority = 0.7

    def items(self):
        return Event.objects.live()

    def lastmod(self, obj):
        return obj.updated_at


class NewsSitemap(Sitemap):
    priority = 0.5

    def items(self):
        return Announcement.objects.visible()

    def lastmod(self, obj):
        return obj.publish_at


class AlbumSitemap(Sitemap):
    priority = 0.4

    def items(self):
        return Album.objects.filter(is_published=True)


SITEMAPS = {"static": StaticSitemap, "events": EventSitemap, "news": NewsSitemap, "albums": AlbumSitemap}
