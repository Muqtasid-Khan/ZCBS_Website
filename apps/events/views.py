from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
import datetime
from django.utils import timezone

from .models import Event, EventCategory


def index(request):
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    year = request.GET.get("year", "")
    when = request.GET.get("when", "all")
    qs = Event.objects.live().select_related("category")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(tagline__icontains=q) | Q(venue__icontains=q))
    if cat:
        qs = qs.filter(category__slug=cat)
    years = sorted({e.academic_year for e in Event.objects.live() if e.academic_year}, reverse=True)
    if year:
        qs = [e for e in qs if e.academic_year == year]
    else:
        qs = list(qs)
    upcoming = sorted([e for e in qs if not e.is_past], key=lambda e: (e.start_at is None, e.start_at))
    past = sorted([e for e in qs if e.is_past], key=lambda e: e.start_at, reverse=True)
    if when == "upcoming":
        past = []
    elif when == "past":
        upcoming = []
    ctx = {"upcoming": upcoming, "past": past, "categories": EventCategory.objects.filter(is_active=True),
           "years": years, "q": q, "cat": cat, "year": year, "when": when,
           "total": len(upcoming) + len(past)}
    return render(request, "events/index.html", ctx)


def archive(request):
    events = Event.objects.visible().filter(status=Event.ARCHIVED).select_related("category")
    return render(request, "events/archive.html", {"events": events})


def _get_event(request, slug):
    ev = get_object_or_404(Event.objects.select_related("category"), slug=slug)
    if not ev.is_visible and not (request.user.is_authenticated and request.user.is_staff):
        raise Http404
    return ev


def _jsonld(request, ev):
    import json
    from apps.core.utils import absolute_url, site_base_url
    data = {"@context": "https://schema.org", "@type": "Event", "name": ev.title,
            "description": ev.summary or ev.tagline,
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "url": site_base_url(request) + ev.get_absolute_url()}
    if ev.start_at:
        data["startDate"] = ev.start_at.isoformat()
    if ev.end_at:
        data["endDate"] = ev.end_at.isoformat()
    if ev.venue:
        data["location"] = {"@type": "Place", "name": ev.venue}
    if ev.card_image:
        data["image"] = absolute_url(request, ev.card_image.url)
    # "</" must never appear inside a <script> block
    return json.dumps(data).replace("</", "<\\/")


def detail(request, slug):
    ev = _get_event(request, slug)
    media = ev.media.filter(is_published=True)
    ctx = {"event": ev,
           "photos": media.filter(kind="photo").exclude(image=""),
           "videos": media.filter(kind="video"),
           "highlights": ev.highlights.filter(kind="highlight"),
           "activities": ev.highlights.filter(kind="activity"),
           "speakers": ev.speakers.all(),
           "organizers": ev.organizers.filter(is_active=True),
           "notices": ev.announcements.visible()[:5],
           "related": ev.related(),
           "preview_hidden": not ev.is_visible, "jsonld": _jsonld(request, ev)}
    return render(request, "events/detail.html", ctx)


def ics(request, slug):
    ev = _get_event(request, slug)
    if not ev.start_at:
        raise Http404
    fmt = "%Y%m%dT%H%M%SZ"
    start = ev.start_at.astimezone(datetime.timezone.utc)
    end = (ev.end_at or ev.start_at + datetime.timedelta(hours=2)).astimezone(datetime.timezone.utc)
    def esc(t):
        return (t or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    body = "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ZCBS//Events//EN", "BEGIN:VEVENT",
                        f"UID:{ev.slug}@zcbs", f"DTSTAMP:{timezone.now().strftime(fmt)}",
                        f"DTSTART:{start.strftime(fmt)}", f"DTEND:{end.strftime(fmt)}",
                        f"SUMMARY:{esc(ev.title)}", f"LOCATION:{esc(ev.venue)}",
                        f"DESCRIPTION:{esc(ev.summary)}", "END:VEVENT", "END:VCALENDAR"])
    resp = HttpResponse(body, content_type="text/calendar")
    resp["Content-Disposition"] = f'attachment; filename="{ev.slug}.ics"'
    return resp
