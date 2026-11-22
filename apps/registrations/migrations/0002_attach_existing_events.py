from django.db import migrations


def attach(apps, schema_editor):
    """Give every event that already exists its own registration settings row.
    The built-in form starts OFF so each existing event keeps exactly the registration box/link it had."""
    Event = apps.get_model("events", "Event")
    Config = apps.get_model("registrations", "EventRegistrationConfig")
    for ev in Event.objects.all():
        Config.objects.get_or_create(event=ev, defaults={"builtin_enabled": False})


class Migration(migrations.Migration):
    dependencies = [("registrations", "0001_initial"), ("events", "0002_seed_categories")]
    operations = [migrations.RunPython(attach, migrations.RunPython.noop)]
