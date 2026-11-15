from django.shortcuts import render

from .models import TeamCategory, TeamMember


def _current_tenure():
    t = TeamMember.objects.filter(is_active=True).order_by("-tenure").values_list("tenure", flat=True).first()
    return t or ""


def index(request):
    tenure = _current_tenure()
    groups = []
    for cat in TeamCategory.objects.filter(is_visible=True):
        members = list(cat.members.filter(is_active=True, tenure=tenure))
        if members:
            groups.append((cat, members))
    featured = TeamMember.objects.filter(is_active=True, is_featured=True, tenure=tenure)
    return render(request, "team/index.html", {"groups": groups, "tenure": tenure, "featured": featured})


def archive(request):
    tenure = _current_tenure()
    old = TeamMember.objects.filter(is_active=True).exclude(tenure=tenure).select_related("category").order_by("-tenure", "category__order", "order")
    by_tenure = {}
    for m in old:
        by_tenure.setdefault(m.tenure, []).append(m)
    return render(request, "team/archive.html", {"by_tenure": by_tenure.items()})
