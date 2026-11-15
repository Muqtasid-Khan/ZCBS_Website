from django.shortcuts import get_object_or_404, render

from .models import Album, MediaCategory, MediaItem


def index(request):
    albums = Album.objects.filter(is_published=True).select_related("event").prefetch_related("items")
    albums = [a for a in albums if a.items.filter(is_published=True).exists() or a.cover]
    videos = MediaItem.objects.filter(kind="video", is_published=True)[:6]
    return render(request, "gallery/index.html", {"albums": albums, "videos": videos})


def album(request, slug):
    al = get_object_or_404(Album, slug=slug, is_published=True)
    items = al.items.filter(is_published=True)
    cat = request.GET.get("category", "")
    if cat:
        items = items.filter(category__slug=cat)
    cats = MediaCategory.objects.filter(items__album=al).distinct()
    return render(request, "gallery/album.html", {
        "album": al, "photos": items.filter(kind="photo").exclude(image=""),
        "videos": items.filter(kind="video"), "cats": cats, "cat": cat})
