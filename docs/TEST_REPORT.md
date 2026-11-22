# Test report

Environment: Linux sandbox, Python 3.12, Django 5.2, SQLite. Date of run: 15 Nov 2026.
**50 automated tests pass** (`python manage.py test tests`), plus the manual/system checks below.

## Verified by automated tests
- Seed data: exactly 22 team members (3 leadership, 15 core, 4 media) with the PDF's names, posts and classes; Zeenat Shahzad = BS AI / BS 2025-29; 5 event categories; 14 homepage sections; 3 role groups; no invented events or news.
- Public pages load: home, about, contact, team, team archive, events, events archive, gallery, news, join, thank-you; custom 404; robots.txt; sitemap.xml.
- A crawler follows every internal link from the homepage (including event/news/gallery pages) with **no broken links**.
- Pending-approval vision/mission/objectives are hidden from the public and visible to logged-in staff; approving publishes them.
- Homepage sections can be hidden/shown and their text edited; intro markup + Skip button present; intro can be switched off.
- Events: creation generates page, slug (unique), album and category listing; draft hidden / staff preview; scheduled publication; upcoming vs past; recap layout; registration block; calendar (.ics); search, category and academic-year filters; archive; duplicate (as draft, original untouched); featured on homepage; new categories; related events.
- Gallery/media: a photo uploaded to an event appears on the event page and album with a single record (no double upload); YouTube embed + invalid-link rejection; replace/delete; oversize and wrong-type uploads rejected.
- News: publish, pin ordering, draft hidden, scheduled, search.
- Membership/contact/newsletter: saved to database, duplicate and invalid-phone rejection, honeypot, closed-membership switch, rate limiting, CSRF enforced.
- Admin: anonymous users redirected to login; dashboard renders (with CREATE NEW EVENT); all admin list/add pages return 200; event created through the real admin form generates a live page; bulk actions (publish/feature/duplicate/archive); team photo upload, promotion between categories; **multi-photo bulk upload** attached to an event; approve/reject + CSV export of applications; site settings edits appear on the site; role permissions (Content Editor blocked from users and applications).

## Verified manually / by system checks
- Clean-room install from `requirements.txt` into a new virtualenv, `migrate`, all tests pass.
- `collectstatic` with WhiteNoise manifest succeeds; **gunicorn in production mode** (DEBUG off) serves all pages with HTTP 200, custom 404, `X-Frame-Options: DENY`, `nosniff`, referrer policy.
- `check --deploy` reports only the optional HSTS-preload note.
- Backup (`backup_site`) then restore into an empty migrated database (`loaddata`): 22 members and 14 sections restored.
- JavaScript files pass `node --check`.

## NOT tested here (please test on your side)
- **Visual/responsive appearance in a real browser.** No browser could be installed in the build sandbox, so I could not screenshot pages, watch the cinematic intro, or test drag-to-reorder and the lightbox/full-screen in a browser. The layouts use Bootstrap breakpoints and were checked as rendered HTML, but expect to tweak spacing after your first look. Test on a phone too.
- **PostgreSQL** (no server available; the driver and URL parsing are configured and standard) and **live Cloudinary uploads** (no credentials). Follow DEPLOYMENT.md and upload one photo after deploying to confirm.
- **Render deployment itself** and **email sending** (the default backend prints to the console; set an SMTP backend if you want emails).
- Large video uploads (limit 90 MB; use YouTube links for longer videos).


## Event registration system (added 22 Nov 2026)
`python manage.py test tests` → **113 tests pass** (61 existing + 52 in `tests/test_registrations.py`, all with fictional data).
Covered: CASPAM ON (1,500 / 2,000, invalid roll, name-only, conflicting mobile/name → review, approve/reject, duplicate roll, tampered price/category ignored, payment state machine, pass activation, one-time check-in, revoked/unpaid/wrong-event denied); CASPAM OFF (no CASPAM fields or matching, normal price, free events, custom/required fields, hidden phone, capacity, deadline, honeypot, rate limit); multiple events (independent switches, separate data, new events auto-configured, legacy events migrated unchanged with their external link); dataset import (CSV/XLSX, hashing, bad files); roles and admin-action permissions; Excel exports (six kinds, freeze panes, filters, no CNIC, formula neutralised).
Migration run on a database that already contained a legacy event: tables created, event attached with built-in form OFF.
**Not tested:** a true two-device simultaneous check-in race (only the single conditional UPDATE is verified), real email/SMS, any payment gateway, production/PostgreSQL, visual layout in real browsers/phones.
