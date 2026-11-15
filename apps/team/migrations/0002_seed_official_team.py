"""Initial team records, copied from the official ZCBS Student Team notification (tenure 2026-2027).
Names, posts and classes are exactly as printed in the notification. Nothing is invented."""
from django.db import migrations

LEAD, CORE, MEDIA = "President and Leadership", "Core Team", "Media Team"
# (name, designation, program, class_label, category)
MEMBERS = [
    ("Muqtasid Khan", "President", "", "BS 2023-27", LEAD),
    ("Arbaz Akram", "Vice President", "", "BS 2023-27", LEAD),
    ("Shumaila", "Vice President", "", "BS 2023-27", LEAD),
    ("Farza Hussain", "General Secretary", "", "BS 2024-28", CORE),
    ("Ibad Jahangir", "General Secretary", "", "BS 2024-28", CORE),
    ("Huma Noor", "Joint Secretary", "", "BS 2024-28", CORE),
    ("Ahmad Hassan", "Joint Secretary", "", "BS 2024-28", CORE),
    ("M. Usman Javaid", "Finance Secretary", "", "BS 2023-27", CORE),
    ("Iqra Ismail", "Finance Secretary", "", "BS 2024-28", CORE),
    ("Ahmad Iqbal", "Information Secretary", "", "BS 2024-28", CORE),
    ("Azra Shahbaz", "Information Secretary", "", "BS 2023-27", CORE),
    ("Zeenat Shahzad", "Executive Member", "BS AI", "BS 2025-29", CORE),
    ("Talha Khan", "Executive Member", "", "BS 2023-27", CORE),
    ("Tayyaba Iftakhar", "Executive Member", "", "BS 2023-27", CORE),
    ("Tania Ramzan", "Executive Member", "", "BS 2023-27", CORE),
    ("Muhammad Mohsin Zaidi", "Executive Member", "", "BS 2026-30", CORE),
    ("Amir Hamza", "Executive Member", "", "BS 2026-30", CORE),
    ("Muhammad Faizan", "Executive Member", "", "BS 2026-30", CORE),
    ("Malaika Mushtaq", "Head", "", "BS 2023-27", MEDIA),
    ("Pari Gull", "Deputy Head", "", "BS 2023-27", MEDIA),
    ("Intezar Mehdi", "Deputy Head", "", "BS 2023-27", MEDIA),
    ("Rao Abdul Rahman Ashraf", "Executive", "", "BS 2023-27", MEDIA),
]
CATS = [(LEAD, "president-and-leadership", "The President and Vice Presidents of the society.", 10),
        (CORE, "core-team", "Secretaries and executive members.", 20),
        (MEDIA, "media-team", "The society's media and communication team.", 30)]


def seed(apps, schema_editor):
    Cat = apps.get_model("team", "TeamCategory")
    Member = apps.get_model("team", "TeamMember")
    cats = {}
    for name, slug, desc, order in CATS:
        cats[name], _ = Cat.objects.get_or_create(name=name, defaults={"slug": slug, "description": desc, "order": order})
    for i, (name, des, prog, cls, cat) in enumerate(MEMBERS, start=1):
        Member.objects.get_or_create(name=name, designation=des, defaults={
            "category": cats[cat], "program": prog, "class_label": cls, "order": i * 10, "tenure": "2026-2027"})


def unseed(apps, schema_editor):
    apps.get_model("team", "TeamMember").objects.filter(tenure="2026-2027").delete()


class Migration(migrations.Migration):
    dependencies = [("team", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
