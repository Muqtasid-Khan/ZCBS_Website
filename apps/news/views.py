from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Announcement, AnnouncementCategory


def index(request):
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    qs = Announcement.objects.visible().select_related("category")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q))
    if cat:
        qs = qs.filter(category__slug=cat)
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "news/index.html", {"page": page, "q": q, "cat": cat,
                                               "categories": AnnouncementCategory.objects.all()})


def detail(request, slug):
    item = get_object_or_404(Announcement, slug=slug)
    from django.utils import timezone
    live = item.status == "published" and item.publish_at <= timezone.now()
    if not live and not (request.user.is_authenticated and request.user.is_staff):
        raise Http404
    others = Announcement.objects.visible().exclude(pk=item.pk)[:3]
    return render(request, "news/detail.html", {"item": item, "others": others, "preview_hidden": not live})
