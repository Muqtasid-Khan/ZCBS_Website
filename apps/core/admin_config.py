from django.contrib.admin.apps import AdminConfig


class ZCBSAdminConfig(AdminConfig):
    default_site = "apps.core.admin_site.ZCBSAdminSite"
