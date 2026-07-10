import io
import logging
import os
import uuid

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC uploads (common from iPhone cameras) will fail validation instead of crashing.

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB — generous for a phone camera photo
TARGET_SIZE = 512  # square thumbnail, plenty for any avatar display size
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


class AvatarUploadError(Exception):
    pass


def _r2_configured() -> bool:
    return bool(
        settings.R2_ACCOUNT_ID
        and settings.R2_ACCESS_KEY_ID
        and settings.R2_SECRET_ACCESS_KEY
        and settings.R2_BUCKET_NAME
        and settings.R2_PUBLIC_URL
    )


def _r2_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _process_image(uploaded_file) -> Image.Image:
    """Shared validation + processing, independent of where the result
    ends up being stored."""
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise AvatarUploadError("Image is too large (max 8MB).")

    try:
        image = Image.open(uploaded_file)
        image.verify()
        # verify() invalidates the file handle for further reads in some
        # Pillow versions — reopen before actually processing pixels.
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
    except (UnidentifiedImageError, OSError):
        raise AvatarUploadError("That file doesn't look like a valid image.")

    # Phone cameras embed orientation in EXIF rather than rotating pixels;
    # without this, "take a photo" uploads often appear sideways.
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    # Center-crop to square, then resize, so avatars display consistently
    # regardless of the source photo's aspect ratio.
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    return image.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)


def save_avatar(user_id: str, uploaded_file, old_avatar_path: str | None) -> str:
    """
    Validates and processes an uploaded avatar image, stores it, and
    returns the URL to save on User.avatar.

    Storage backend:
      - Cloudflare R2 (S3-compatible object storage) when R2_ACCOUNT_ID /
        R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / R2_BUCKET_NAME /
        R2_PUBLIC_URL are all configured — this is REQUIRED for production.
        Django does not serve files from MEDIA_ROOT when DEBUG=False (see
        config/urls.py), so local-disk storage silently breaks every avatar
        upload in production: the file writes successfully, but the URL
        returned to the frontend 404s, which is exactly what a broken
        <img> in the app means.
      - Local disk (MEDIA_ROOT/avatars/) as a fallback when R2 isn't
        configured, purely so local development doesn't require setting up
        a Cloudflare account just to test the avatar upload flow. Do not
        rely on this in production.

    Accepts whatever the browser sends from either a file picker ("choose
    from gallery") or `<input capture>` ("take a photo") — both arrive as
    the same multipart file upload from the frontend's point of view.
    """
    image = _process_image(uploaded_file)
    filename = f"{uuid.uuid4().hex}.jpg"

    if _r2_configured():
        return _save_to_r2(image, filename, old_avatar_path)

    logger.warning(
        "R2 is not configured — saving avatar to local disk. This WILL NOT "
        "work in production (Django doesn't serve MEDIA files when DEBUG=False). "
        "Set R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / "
        "R2_BUCKET_NAME / R2_PUBLIC_URL before deploying."
    )
    return _save_to_local_disk(image, filename, old_avatar_path)


def _save_to_r2(image: Image.Image, filename: str, old_avatar_path: str | None) -> str:
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)
    buffer.seek(0)

    key = f"avatars/{filename}"
    client = _r2_client()
    try:
        client.put_object(
            Bucket=settings.R2_BUCKET_NAME,
            Key=key,
            Body=buffer,
            ContentType="image/jpeg",
            CacheControl="public, max-age=31536000, immutable",
        )
    except Exception as exc:
        logger.exception("Failed to upload avatar to R2")
        raise AvatarUploadError("Couldn't save the image right now — please try again.") from exc

    public_base = settings.R2_PUBLIC_URL.rstrip("/")

    # Clean up the previous uploaded avatar (only if it was one of ours —
    # never try to delete a Google/DiceBear URL, and skip anything that
    # isn't actually stored in this bucket, e.g. a leftover local-disk path
    # from before R2 was configured).
    if old_avatar_path and old_avatar_path.startswith(public_base):
        old_key = old_avatar_path[len(public_base) :].lstrip("/")
        try:
            client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=old_key)
        except Exception:
            logger.exception("Failed to delete old avatar from R2 (non-fatal): %s", old_key)

    return f"{public_base}/{key}"


def _save_to_local_disk(image: Image.Image, filename: str, old_avatar_path: str | None) -> str:
    avatars_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
    os.makedirs(avatars_dir, exist_ok=True)

    full_path = os.path.join(avatars_dir, filename)
    image.save(full_path, "JPEG", quality=88)

    if old_avatar_path and not old_avatar_path.startswith("http"):
        old_full_path = os.path.join(settings.MEDIA_ROOT, old_avatar_path)
        if os.path.exists(old_full_path):
            try:
                os.remove(old_full_path)
            except OSError:
                pass

    return f"avatars/{filename}"