from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Website"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from .roles import create_roles
        post_migrate.connect(create_roles)
