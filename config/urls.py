from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.core.sitemaps import SITEMAPS
from apps.core import views as core_views

handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", core_views.robots_txt, name="robots"),
    path("favicon.ico", core_views.favicon_ico, name="favicon"),
    path("", include("apps.core.urls")),
    path("team/", include("apps.team.urls")),
    path("events/", include("apps.events.urls")),
    path("gallery/", include("apps.gallery.urls")),
    path("news/", include("apps.news.urls")),
    path("join/", include("apps.membership.urls")),
    path("registrations/", include("apps.registrations.urls")),
]
if settings.DEBUG or not settings.USE_CLOUDINARY:
    # Local media serving (development, or small deployments without Cloudinary)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
