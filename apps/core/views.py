from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.events.models import Event
from apps.gallery.models import Album, MediaItem
from apps.membership.models import MembershipApplication
from apps.news.models import Announcement
from apps.team.models import TeamCategory, TeamMember

from .forms import ContactForm, NewsletterForm
from .models import ContentBlock, HomeSection, NewsletterSubscriber, PageContent, SiteSettings
from .utils import rate_limited, visible_blocks


def home(request):
    site = SiteSettings.load()
    sections = list(HomeSection.objects.filter(is_visible=True))
    keys = {s.key for s in sections}
    ctx = {"sections": sections}
    if "about" in keys or "vision_mission" in keys or "objectives" in keys:
        blocks = visible_blocks(ContentBlock.objects.all(), request, site)
        ctx["vision"] = blocks.filter(kind="vision").first()
        ctx["mission"] = blocks.filter(kind="mission").first()
        ctx["objectives"] = blocks.filter(kind="objective")[:6]
    if "upcoming_events" in keys:
        feat = list(Event.objects.upcoming().filter(is_featured=True).select_related("category")[:3])
        if len(feat) < 3:
            more = Event.objects.upcoming().exclude(pk__in=[e.pk for e in feat]).order_by("start_at").select_related("category")
            feat += list(more[: 3 - len(feat)])
        ctx["upcoming"] = feat
    if "recent_events" in keys:
        recent = Event.objects.past().select_related("category").order_by("-start_at")
        ctx["recent"] = list(recent.filter(is_featured=True)[:3]) or list(recent[:3])
    if "announcements" in keys:
        ctx["announcements"] = Announcement.objects.visible()[:4]
    for k, slug in (("leadership", "president-and-leadership"), ("core_team", "core-team"), ("media_team", "media-team")):
        if k in keys:
            cat = TeamCategory.objects.filter(slug=slug, is_visible=True).first()
            members = TeamMember.objects.filter(category=cat, is_active=True)[:8] if cat else []
            ctx[k] = list(members)
    if "gallery" in keys:
        ctx["gallery_items"] = list(MediaItem.objects.filter(kind="photo", is_published=True).exclude(image="")[:8])
    if "stats" in keys and site.show_stats:
        now_events = Event.objects.live()
        stats = [("Events organised", Event.objects.past().count()),
                 ("Upcoming events", Event.objects.upcoming().count()),
                 ("Team members", TeamMember.objects.filter(is_active=True).count()),
                 ("Photo albums", Album.objects.filter(is_published=True, items__isnull=False).distinct().count())]
        ctx["stats"] = [s for s in stats if s[1]]
    return render(request, "core/home.html", ctx)


def about(request):
    site = SiteSettings.load()
    page = PageContent.objects.filter(slug="about").first()
    if page and page.approval != "approved" and not request.user.is_staff and not site.show_pending_publicly:
        page = None
    blocks = visible_blocks(ContentBlock.objects.all(), request, site)
    by_kind = {k: list(blocks.filter(kind=k)) for k, _ in ContentBlock.KINDS}
    return render(request, "core/about.html", {"page": page, "by_kind": by_kind,
                                               "has_pending": blocks.filter(approval="pending").exists() and request.user.is_staff,
                                               "timeline": _timeline()})


def _timeline():
    evs = Event.objects.past().select_related("category").order_by("-start_at")[:12]
    years = {}
    for e in evs:
        years.setdefault(e.start_at.year, []).append(e)
    return sorted(years.items(), reverse=True)


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST":
        if rate_limited(request, "contact"):
            messages.error(request, "Too many messages from this connection. Please try again later.")
        elif form.is_valid():
            form.save()
            messages.success(request, "Thank you. Your message has reached the ZCBS team.")
            return redirect("core:contact")
    return render(request, "core/contact.html", {"form": form})


@require_POST
def newsletter(request):
    form = NewsletterForm(request.POST)
    if rate_limited(request, "newsletter"):
        messages.error(request, "Too many attempts. Please try again later.")
    elif form.is_valid():
        sub, created = NewsletterSubscriber.objects.get_or_create(email=form.cleaned_data["email"].lower())
        if not sub.is_active:
            sub.is_active = True
            sub.save()
        messages.success(request, "You are subscribed. Thank you.")
    else:
        messages.error(request, "Please enter a valid email address.")
    dest = request.META.get("HTTP_REFERER", "/")
    from django.utils.http import url_has_allowed_host_and_scheme
    if not url_has_allowed_host_and_scheme(dest, allowed_hosts={request.get_host()}):
        dest = "/"
    return redirect(dest)


def robots_txt(request):
    from django.conf import settings
    lines = ["User-agent: *", f"Disallow: /{settings.ADMIN_URL}", f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
