# Deployment: GitHub → Render (PostgreSQL) + Cloudinary

You own every piece: the GitHub repo, the Render service and database, the Cloudinary account, the domain. Create these accounts with a
**society email address** (not a personal one) and share the recovery details with the incoming President.

## 1. Put the code on GitHub
```powershell
git init
git add .
git commit -m "ZCBS website"
git branch -M main
git remote add origin https://github.com/<your-account>/zcbs-website.git
git push -u origin main
```
(`.env`, database, media and backups are excluded by `.gitignore`.)

## 2. Cloudinary (image & video storage)
1. Sign up at cloudinary.com. In the dashboard copy the **API Environment variable**: `cloudinary://API_KEY:API_SECRET@CLOUD_NAME`.
2. Keep it for step 3 as `CLOUDINARY_URL`.
Render's disk is wiped on every deploy, so Cloudinary is what keeps uploaded photos permanently.

## 3. Render (website + PostgreSQL)
**One-click:** Render → New → **Blueprint** → select your GitHub repo (it reads `render.yaml`, creating `zcbs-website` and `zcbs-db`).
Then open the web service → Environment and set `CLOUDINARY_URL`.
**Manual alternative:** New → PostgreSQL (copy the *Internal Database URL*); New → Web Service → connect repo →
Build command `./build.sh`, Start command `gunicorn config.wsgi:application --workers 2 --timeout 60`, and add environment variables:

| Variable | Value |
|---|---|
| `DEBUG` | `False` |
| `SECRET_KEY` | long random text (Render can generate it) |
| `DATABASE_URL` | Internal Database URL of your Render PostgreSQL |
| `CLOUDINARY_URL` | from step 2 |
| `ADMIN_URL` | e.g. `zcbs-control-7k2/` (private dashboard address) |
| `ALLOWED_HOSTS` | your custom domain(s), comma separated (the `*.onrender.com` host is added automatically) |
| `CSRF_TRUSTED_ORIGINS` | `https://yourdomain.com` (custom domain only) |

`build.sh` installs packages, collects static files and runs migrations (this also loads the 22 team members on first deploy).

## 4. Create the administrator on Render
Web service → **Shell** tab → `python manage.py createsuperuser`. (If your plan has no Shell, run it from your own computer with
`DATABASE_URL` set in `.env` to the *External* database URL, then remove that line again.)

## 5. Domain
Render → web service → Settings → Custom Domains → add your domain and create the DNS records Render shows at your registrar.
Then add the domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

## 6. Backups and recovery
- **Database:** Render paid PostgreSQL plans include automatic backups; the free plan database expires after a limited period — upgrade
  or export regularly. Manual export: `pg_dump "<External Database URL>" > zcbs-backup.sql` (needs PostgreSQL client tools).
- **Content snapshot (any database):** `python manage.py backup_site` creates `backups/zcbs-backup-*.zip` (JSON data + local media).
- **Images:** stored in Cloudinary — they survive redeploys; download from Cloudinary → Media Library if you need an offline copy.
- **Restore:** deploy the code, `python manage.py migrate` on an empty database, then
  `python manage.py loaddata zcbs-data-*.json` (and copy `media/` back if you used local storage).
- **Code:** it is the GitHub repo. Keep at least two people as owners of the GitHub organisation.

## 7. Updating the site later
Dashboard changes need no deployment. Code changes: edit, `git push`, Render redeploys automatically.
