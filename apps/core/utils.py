from django.conf import settings
from django.core.cache import cache


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "unknown"))


def rate_limited(request, bucket):
    """True when this IP has submitted `bucket` forms too often in the last hour."""
    key = f"rl:{bucket}:{client_ip(request)}"
    n = cache.get(key, 0)
    if n >= settings.FORM_RATE_LIMIT_PER_HOUR:
        return True
    cache.set(key, n + 1, 3600)
    return False


def visible_blocks(qs, request, site):
    """Pending-approval drafts are shown only to logged-in staff (as a preview)."""
    if request.user.is_authenticated and request.user.is_staff:
        return qs
    if site.show_pending_publicly:
        return qs
    return qs.filter(approval="approved")


def site_base_url(request):
    """Public address of the website with no trailing slash.
    Uses the SITE_URL setting when it is set, so Google always sees ONE address
    (and not a preview/deployment address); otherwise the address of the request."""
    configured = getattr(settings, "SITE_URL", "")
    return configured if configured else f"{request.scheme}://{request.get_host()}"


def absolute_url(request, url):
    """Turn "/static/x.png" into a full address; leave full addresses (e.g. Cloudinary) alone."""
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return site_base_url(request) + url
