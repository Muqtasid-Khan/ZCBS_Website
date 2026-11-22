"""Creates the three role groups after every migrate (idempotent)."""
ROLES = {
    "Website Administrator": None,  # all permissions on every ZCBS app
    "Content Editor": {
        "team": "*", "events": "*", "gallery": "*", "news": "*",
        "core": ["homesection", "pagecontent", "contentblock"],
    },
    "Membership Manager": {"membership": "*", "core": ["contactsubmission", "newslettersubscriber"]},
}
APP_LABELS = ["core", "team", "events", "gallery", "news", "membership", "registrations"]


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


# Event-registration roles: exact permissions by (app, codename). Check-in staff need "Staff status" ticked to sign in.
R = "registrations"
REGISTRATION_ROLES = {
    "Super Admin": "ALL",   # every permission of every ZCBS app
    "Event Manager": [
        (R, c) for c in ["view_registration", "view_dashboard", "export_registrations", "verify_student", "upload_dataset",
                         "view_eventregistrationconfig", "change_eventregistrationconfig",
                         "add_registrationfield", "change_registrationfield", "delete_registrationfield", "view_registrationfield",
                         "add_paymentmethod", "change_paymentmethod", "delete_paymentmethod", "view_paymentmethod",
                         "add_studentdataset", "change_studentdataset", "delete_studentdataset", "view_studentdataset",
                         "view_authorizedstudent", "manage_pass"]
    ] + [("events", c) for c in ["view_event", "change_event", "add_event"]],
    "Finance Manager": [(R, c) for c in ["view_registration", "view_dashboard", "approve_payment", "export_registrations",
                                         "view_eventregistrationconfig", "view_paymentmethod"]],
    "Check-in Staff": [(R, "perform_checkin")],
}


def create_registration_roles(sender=None, **kwargs):
    from django.contrib.auth.models import Group, Permission
    for role, spec in REGISTRATION_ROLES.items():
        group, _ = Group.objects.get_or_create(name=role)
        if spec == "ALL":
            perms = Permission.objects.filter(content_type__app_label__in=APP_LABELS)
        else:
            ids = []
            for app, code in spec:
                p = Permission.objects.filter(content_type__app_label=app, codename=code).first()
                if p:
                    ids.append(p.pk)
            perms = Permission.objects.filter(pk__in=ids)
        group.permissions.set(perms)
