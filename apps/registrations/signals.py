def ensure_config(sender, instance, created, **kwargs):
    """Every event (existing or future) automatically owns a registration configuration.
    Brand-new events start with the built-in form ON; events migrated from the old
    system keep their old behaviour until an administrator switches the built-in form on."""
    from .models import EventRegistrationConfig
    if kwargs.get("raw"):
        return
    EventRegistrationConfig.objects.get_or_create(
        event=instance, defaults={"builtin_enabled": created and not instance.registration_url})
