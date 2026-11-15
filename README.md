# ZCBS Website — Zakariyan Character Building Society (CASPAM Chapter, BZU Multan)

A complete Django website with a branded administration dashboard, reusable event-management system,
media library, news, team and membership management. **Everything is edited from the dashboard — no code needed.**

| Part | Technology |
|---|---|
| Backend | Python 3.12, Django 5.2 |
| Database | SQLite locally, PostgreSQL on Render |
| Images/videos | Local `media/` folder, or Cloudinary when `CLOUDINARY_URL` is set |
| Static files | WhiteNoise |
| Rich text | CKEditor 5 |
| Frontend | HTML5, CSS3, vanilla JavaScript, Bootstrap 5, Bootstrap Icons (all bundled in `static/vendor`, fonts self-hosted) |

Docs: [`docs/ADMIN_GUIDE.md`](docs/ADMIN_GUIDE.md) · [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) · [`docs/BRAND_GUIDE.md`](docs/BRAND_GUIDE.md) · [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md)

## 1. Run it on Windows (first time)

Install **Python 3.12** from python.org (tick *"Add python.exe to PATH"*) and **Git**. Then in PowerShell, inside this folder:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then open .env in Notepad and set SECRET_KEY to any long random text
python manage.py migrate        # creates the database AND loads the 22 official team members
python manage.py createsuperuser   # your administrator login (use a strong password, 10+ characters)
python manage.py runserver
```

Open **http://127.0.0.1:8000/** (website) and **http://127.0.0.1:8000/admin/** (dashboard).
Next time you only need: `venv\Scripts\activate` then `python manage.py runserver`.

Optional: `python manage.py seed_demo` adds clearly labelled **[DEMO]** events/news so you can preview layouts;
`python manage.py seed_demo --remove` deletes them.

## 2. Project layout

```
config/            settings, urls, wsgi
apps/core/         site settings, homepage sections, menus, About content, contact, roles, admin look
apps/team/         team categories and members (22 official records are loaded by migration)
apps/events/       event categories, events, highlights, speakers, automatic event pages
apps/gallery/      albums, media library, bulk upload, lightbox data
apps/news/         announcements
apps/membership/   applications and interest areas
templates/ static/ HTML templates, CSS, JS, bundled Bootstrap, brand/logo files
tools/make_brand.py  regenerates every logo file from one source
tests/             automated tests (50)
```

## 3. Commands

| Command | Purpose |
|---|---|
| `python manage.py runserver` | run locally |
| `python manage.py test tests` | run all automated tests |
| `python manage.py backup_site` | ZIP with database JSON + local media in `backups/` |
| `python manage.py createsuperuser` | new administrator |
| `python tools/make_brand.py` | regenerate logos (needs `pip install cairosvg fonttools brotli`) |

## 4. Security notes
Passwords are hashed (PBKDF2), CSRF protection is on, uploads are validated by type and size, forms have honeypot + rate limiting,
production forces HTTPS/secure cookies/HSTS, and `ADMIN_URL` in `.env` lets you move the dashboard from `/admin/` to a private address.
Rich-text content is entered only by logged-in staff and rendered as written, so give dashboard accounts only to people you trust.
Never commit `.env` to GitHub (it is already in `.gitignore`).
