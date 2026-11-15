from django.contrib import messages
from django.shortcuts import redirect, render

from apps.core.models import SiteSettings
from apps.core.utils import rate_limited

from .forms import ApplicationForm


def join(request):
    site = SiteSettings.load()
    form = ApplicationForm(request.POST or None)
    if request.method == "POST" and site.membership_open:
        if rate_limited(request, "join"):
            messages.error(request, "Too many submissions from this connection. Please try again later.")
        elif form.is_valid():
            app = form.save(commit=False)
            app.save()
            form.save_m2m()
            return redirect("membership:thanks")
    return render(request, "membership/join.html", {"form": form})


def thanks(request):
    return render(request, "membership/thanks.html")
