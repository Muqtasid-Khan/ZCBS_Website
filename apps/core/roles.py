"""Creates the three role groups after every migrate (idempotent)."""
ROLES = {
    "Website Administrator": None,  # all permissions on every ZCBS app
    "Content Editor": {
        "team": "*", "events": "*", "gallery": "*", "news": "*",
        "core": ["homesection", "pagecontent", "contentblock"],
    },
    "Membership Manager": {"membership": "*", "core": ["contactsubmission", "newslettersubscriber"]},
}
APP_LABELS = ["core", "team", "events", "gallery", "news", "membership"]


def create_roles(sender=None, **kwargs):
    from django.contrib.auth.models import Group, Permission
    for role, spec in ROLES.items():
        group, _ = Group.objects.get_or_create(name=role)
        perms = Permission.objects.filter(content_type__app_label__in=APP_LABELS)
        if spec is not None:
            ids = []
            for p in perms.select_related("content_type"):
                allowed = spec.get(p.content_type.app_label)
                if allowed == "*" or (allowed and p.content_type.model in allowed):
                    ids.append(p.pk)
            perms = Permission.objects.filter(pk__in=ids)
        group.permissions.set(perms)
