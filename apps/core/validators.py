import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.utils.deconstruct import deconstructible

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v"}


def validate_image_file(f):
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in IMAGE_EXT:
        raise ValidationError("Unsupported image type. Use JPG, PNG, WebP or GIF.")
    limit = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
    if f.size > limit:
        raise ValidationError(f"Image is too large ({f.size/1048576:.1f} MB). Maximum is {settings.MAX_IMAGE_UPLOAD_MB} MB.")


def validate_video_file(f):
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in VIDEO_EXT:
        raise ValidationError("Unsupported video type. Use MP4, WebM or MOV (or paste a YouTube/Vimeo link instead).")
    limit = settings.MAX_VIDEO_UPLOAD_MB * 1024 * 1024
    if f.size > limit:
        raise ValidationError(f"Video is too large ({f.size/1048576:.0f} MB). Maximum is {settings.MAX_VIDEO_UPLOAD_MB} MB — "
                              "for longer videos upload to YouTube and paste the link.")


def video_storage():
    """Videos need Cloudinary's video storage class when Cloudinary is in use."""
    if getattr(settings, "USE_CLOUDINARY", False):
        from cloudinary_storage.storage import VideoMediaCloudinaryStorage
        return VideoMediaCloudinaryStorage()
    return default_storage
