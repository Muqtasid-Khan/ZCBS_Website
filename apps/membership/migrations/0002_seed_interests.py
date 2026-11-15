from django.db import migrations

AREAS = ["Leadership", "Public speaking & communication", "Writing & debate", "Event management",
         "Media, photography & design", "Research & academics", "Community service", "Sports & recreation"]


def seed(apps, schema_editor):
    A = apps.get_model("membership", "InterestArea")
    for i, n in enumerate(AREAS, start=1):
        A.objects.get_or_create(name=n, defaults={"order": i * 10})


class Migration(migrations.Migration):
    dependencies = [("membership", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
