from django.db import migrations

CATS = ["Announcements", "Official Notices", "Society Updates", "Activity Reports", "Important Information"]


def seed(apps, schema_editor):
    from django.utils.text import slugify
    C = apps.get_model("news", "AnnouncementCategory")
    for i, n in enumerate(CATS, start=1):
        C.objects.get_or_create(slug=slugify(n), defaults={"name": n, "order": i * 10})


class Migration(migrations.Migration):
    dependencies = [("news", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
