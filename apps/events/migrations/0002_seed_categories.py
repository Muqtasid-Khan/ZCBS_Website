from django.db import migrations

CATS = [
    ("Orientation & Welcome Events", "orientation-welcome", "Orientation sessions, welcome ceremonies and new student introductions.", "bi-door-open"),
    ("Intellectual & Academic Activities", "intellectual-academic", "Expert sessions, guest speakers, interview preparation, Two-Minute Spotlight, discussions and knowledge competitions.", "bi-lightbulb"),
    ("Leadership & Personal Development", "leadership-development", "Leadership workshops, communication sessions, personality development and mock interviews.", "bi-compass"),
    ("Cultural & Recreational Events", "cultural-recreational", "Fun Fair, Sports Gala, Annual Dinner and cultural or recreational activities.", "bi-trophy"),
    ("Special Events", "special-events", "Special campaigns, collaborative activities and future initiatives.", "bi-stars"),
]


def seed(apps, schema_editor):
    C = apps.get_model("events", "EventCategory")
    for i, (n, s, d, ic) in enumerate(CATS, start=1):
        C.objects.get_or_create(slug=s, defaults={"name": n, "description": d, "icon": ic, "order": i * 10})


class Migration(migrations.Migration):
    dependencies = [("events", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
