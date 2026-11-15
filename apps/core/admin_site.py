from django.contrib.admin import AdminSite
from django.urls import reverse


class ZCBSAdminSite(AdminSite):
    site_header = "ZCBS Dashboard"
    site_title = "ZCBS Dashboard"
    index_title = "Manage your website"
    index_template = "admin/zcbs_index.html"
    ORDER = ["events", "gallery", "news", "team", "membership", "core", "auth"]

    def get_app_list(self, request, app_label=None):
        apps = super().get_app_list(request, app_label)
        apps.sort(key=lambda a: self.ORDER.index(a["app_label"]) if a["app_label"] in self.ORDER else 99)
        return apps

    def index(self, request, extra_context=None):
        from apps.core.models import ContactSubmission
        from apps.events.models import Event
        from apps.membership.models import MembershipApplication
        from apps.news.models import Announcement
        extra = {
            "pending_applications": MembershipApplication.objects.filter(status="pending").count(),
            "draft_events": Event.objects.filter(status="draft").count(),
            "draft_news": Announcement.objects.filter(status="draft").count(),
            "unhandled_messages": ContactSubmission.objects.filter(is_handled=False).count(),
            "new_event_url": reverse("admin:events_event_add"),
        }
        extra.update(extra_context or {})
        return super().index(request, extra)
