"""Backup everything: database content (JSON) and locally stored media (ZIP).
Usage:  python manage.py backup_site          ->  backups/zcbs-backup-YYYYMMDD-HHMM.zip
Restore: python manage.py loaddata <the .json inside the zip>   (after `migrate` on an empty database)
When Cloudinary is used, images live in your Cloudinary account (download them from there)."""
import datetime
import io
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a backup ZIP of database content and local media."

    def handle(self, *args, **opts):
        out_dir = Path(settings.BASE_DIR) / "backups"
        out_dir.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        target = out_dir / f"zcbs-backup-{stamp}.zip"
        buf = io.StringIO()
        call_command("dumpdata", "--natural-foreign", "--natural-primary", "--indent", "1",
                     "--exclude", "contenttypes", "--exclude", "auth.permission", "--exclude", "sessions",
                     "--exclude", "admin.logentry", stdout=buf)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"zcbs-data-{stamp}.json", buf.getvalue())
            media = Path(settings.MEDIA_ROOT)
            if media.exists():
                for f in media.rglob("*"):
                    if f.is_file():
                        z.write(f, f"media/{f.relative_to(media)}")
        self.stdout.write(self.style.SUCCESS(f"Backup written to {target}"))
