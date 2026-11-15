from django.utils import timezone

from .models import NavItem, SiteSettings


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
    }
