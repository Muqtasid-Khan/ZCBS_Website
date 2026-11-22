from django.apps import AppConfig
from django.db.models.signals import post_save


class RegistrationsConfig(AppConfig):
    name = "apps.registrations"
    verbose_name = "Event Registrations"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from apps.events.models import Event
        from .signals import ensure_config
        post_save.connect(ensure_config, sender=Event, dispatch_uid="registrations_ensure_config")
