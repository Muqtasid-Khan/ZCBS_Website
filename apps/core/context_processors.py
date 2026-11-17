import json

from django.conf import settings
from django.templatetags.static import static
from django.utils import timezone
from django.utils.safestring import mark_safe

from .models import NavItem, SiteSettings


def _search_data(request, s):
    """Structured data (JSON-LD) that tells Google who ZCBS is: name, alternative names, logo, social profiles."""
    home = request.build_absolute_uri("/")
    names = [n for n in [s.short_name, f"{s.short_name} {s.chapter_line}".strip()] if n]
    organization = {
        "@type": "Organization", "@id": home + "#organization",
        "name": s.site_name, "alternateName": names, "url": home,
        "logo": request.build_absolute_uri(static("brand/favicon-512.png")),
    }
    if s.seo_description:
        organization["description"] = s.seo_description
    same_as = [x["url"] for x in s.socials]
    if same_as:
        organization["sameAs"] = same_as
    website = {"@type": "WebSite", "@id": home + "#website", "url": home,
               "name": s.short_name or s.site_name, "alternateName": [s.site_name],
               "publisher": {"@id": home + "#organization"}}
    data = {"@context": "https://schema.org", "@graph": [organization, website]}
    # "<" is escaped so the data can never end the script tag early.
    return mark_safe(json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))


def site(request):
    if request.path.startswith("/static/") or request.path.startswith("/media/"):
        return {}
    s = SiteSettings.load()
    items = list(NavItem.objects.filter(is_visible=True))
    return {
        "site": s,
        "nav_header": [i for i in items if i.location == NavItem.HEADER],
        "nav_footer": [i for i in items if i.location == NavItem.FOOTER],
        "current_year": timezone.now().year,
        "is_preview": request.user.is_authenticated and request.user.is_staff,
        "search_jsonld": _search_data(request, s),
        "google_verification": getattr(settings, "GOOGLE_SITE_VERIFICATION", ""),
    }
