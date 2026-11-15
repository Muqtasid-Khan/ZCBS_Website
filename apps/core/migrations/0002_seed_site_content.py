"""Starting content. Everything here is editable in the dashboard.
Vision, mission, objectives, values and the About text are drafts marked PENDING APPROVAL:
they stay hidden from the public until the President approves them. No history, partnerships or
achievements are claimed anywhere."""
from django.db import migrations

HOME = [
    # key, eyebrow, heading, body, button_label, button_url
    ("hero", "CASPAM · Bahauddin Zakariya University, Multan", "Where character is built and leaders are made.",
     "The Zakariyan Character Building Society nurtures integrity, communication and leadership in the students of BZU Multan.",
     "Join ZCBS", "/join/"),
    ("about", "About ZCBS", "A society devoted to the whole student",
     "ZCBS is the character-building society of the CASPAM chapter at Bahauddin Zakariya University, Multan. We focus on leadership, intellectual growth, communication, discipline, creativity, ethics and teamwork.",
     "Read more about us", "/about/"),
    ("vision_mission", "Our direction", "Vision & mission", "", "", ""),
    ("objectives", "What we work towards", "Core objectives", "", "", ""),
    ("stats", "At a glance", "ZCBS in numbers", "", "", ""),
    ("upcoming_events", "Do not miss", "Upcoming events", "", "All events", "/events/"),
    ("recent_events", "Event stories", "Recent highlights", "", "Browse past events", "/events/?when=past"),
    ("announcements", "Stay informed", "Latest announcements", "", "All announcements", "/news/"),
    ("leadership", "The people behind ZCBS", "Leadership", "", "Meet the whole team", "/team/"),
    ("core_team", "Working for the society", "Core team", "", "Meet the whole team", "/team/"),
    ("media_team", "Telling our story", "Media team", "", "Meet the whole team", "/team/"),
    ("gallery", "Moments", "Gallery highlights", "", "Open the gallery", "/gallery/"),
    ("membership", "Be part of it", "Become a member of ZCBS",
     "Apply to join the society, take part in its activities and grow with fellow students.", "Apply now", "/join/"),
    ("social", "Follow ZCBS", "Stay connected", "", "", ""),
]
NAV = [("Home", "/", "header"), ("About", "/about/", "header"), ("Team", "/team/", "header"), ("Events", "/events/", "header"),
       ("Gallery", "/gallery/", "header"), ("News", "/news/", "header"), ("Join ZCBS", "/join/", "header"),
       ("Contact", "/contact/", "header"),
       ("About ZCBS", "/about/", "footer"), ("Our Team", "/team/", "footer"), ("Events & Activities", "/events/", "footer"),
       ("Past Events", "/events/?when=past", "footer"), ("Gallery", "/gallery/", "footer"), ("News", "/news/", "footer"),
       ("Join ZCBS", "/join/", "footer"), ("Contact", "/contact/", "footer")]

ABOUT_INTRO = ("<p>The Zakariyan Character Building Society (ZCBS), CASPAM Chapter, is the student society of Bahauddin Zakariya "
               "University, Multan, dedicated to character development, leadership, intellectual growth, communication, discipline, "
               "creativity, ethics, teamwork and student engagement.</p>"
               "<p>Through sessions, workshops, competitions and cultural activities, the society gives students a place to practise "
               "the qualities that a degree alone cannot teach.</p>")

# kind, title, text, icon
BLOCKS = [
    ("vision", "Our vision", "To be a student community where character, knowledge and leadership grow together, so that every member graduates as a confident, ethical and contributing citizen.", "bi-eye"),
    ("mission", "Our mission", "To create a welcoming platform of sessions, discussions, competitions and shared experiences through which students of BZU develop integrity, communication skills, leadership and a sense of responsibility towards society.", "bi-bullseye"),
    ("objective", "Build strong character", "Encourage honesty, discipline and ethical conduct in everyday student life.", "bi-shield-check"),
    ("objective", "Develop leadership", "Give students real opportunities to organise, lead and take responsibility.", "bi-compass"),
    ("objective", "Strengthen communication", "Help members speak, listen and present with clarity and confidence.", "bi-mic"),
    ("objective", "Grow intellectually", "Promote curiosity through expert sessions, discussions and knowledge-based activities.", "bi-lightbulb"),
    ("objective", "Prepare for professional life", "Support interview preparation, personality development and professional readiness.", "bi-briefcase"),
    ("objective", "Build community", "Bring students together through cultural and recreational activities.", "bi-people"),
    ("value", "Integrity", "Acting honestly and consistently, in public and in private.", "bi-shield-check"),
    ("value", "Respect", "Valuing every voice, background and point of view.", "bi-heart"),
    ("value", "Discipline", "Doing what is right and what was promised, on time.", "bi-clock"),
    ("value", "Teamwork", "Achieving more together than alone.", "bi-diagram-3"),
    ("value", "Curiosity", "Learning continuously and asking good questions.", "bi-search"),
    ("value", "Service", "Using our abilities for the benefit of others.", "bi-hand-thumbs-up"),
    ("approach", "Character through practice", "Character is built by doing. ZCBS activities are designed so that members practise speaking, leading, organising and collaborating, not only listening about them.", "bi-hammer"),
    ("leadership", "Leadership as responsibility", "We see leadership as service and responsibility rather than position. Every member is encouraged to lead something, however small.", "bi-flag"),
    ("development", "Student development", "Sessions, mentoring and hands-on roles help students grow academically, socially and professionally during their time at university.", "bi-graph-up-arrow"),
    ("purpose", "Activities and purpose", "From orientation and expert sessions to workshops, competitions and annual cultural events, every activity serves the society's purpose of developing well-rounded students.", "bi-calendar-event"),
]


def seed(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    HomeSection = apps.get_model("core", "HomeSection")
    NavItem = apps.get_model("core", "NavItem")
    PageContent = apps.get_model("core", "PageContent")
    ContentBlock = apps.get_model("core", "ContentBlock")
    SiteSettings.objects.get_or_create(pk=1, defaults={
        "footer_text": "The student character-building society of the CASPAM chapter, Bahauddin Zakariya University, Multan.",
        "seo_title": "Zakariyan Character Building Society | CASPAM, BZU Multan",
        "seo_description": "Official website of the Zakariyan Character Building Society (ZCBS), CASPAM Chapter, Bahauddin Zakariya University, Multan.",
        "membership_intro": "<p>Become part of a student community that values character, leadership and growth. Fill in the form below and the ZCBS team will review your application.</p>",
        "contact_intro": "Questions, suggestions or collaboration ideas? Write to the ZCBS team.",
    })
    for i, (k, eb, h, b, bl, bu) in enumerate(HOME, start=1):
        HomeSection.objects.get_or_create(key=k, defaults={"eyebrow": eb, "heading": h, "body": b, "button_label": bl,
                                                           "button_url": bu, "order": i * 10})
    for i, (l, u, loc) in enumerate(NAV, start=1):
        NavItem.objects.get_or_create(label=l, url=u, location=loc, defaults={"order": i * 10})
    PageContent.objects.get_or_create(slug="about", defaults={
        "title": "About ZCBS", "subtitle": "Zakariyan Character Building Society · CASPAM Chapter",
        "body": ABOUT_INTRO, "approval": "pending",
        "seo_description": "About the Zakariyan Character Building Society (ZCBS), CASPAM Chapter, BZU Multan."})
    for i, (kind, title, text, icon) in enumerate(BLOCKS, start=1):
        ContentBlock.objects.get_or_create(kind=kind, title=title, defaults={"text": text, "icon": icon,
                                                                           "approval": "pending", "order": i * 10})


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
