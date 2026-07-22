import io
import logging
import os
import uuid

import requests
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
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
REQUEST_TIMEOUT = 15

# L3: be explicit about the decompression-bomb pixel ceiling rather than
# relying implicitly on Pillow's own default threshold.
Image.MAX_IMAGE_PIXELS = 89_478_485


class AvatarUploadError(Exception):
    pass


def _supabase_configured() -> bool:
    return bool(
        settings.SUPABASE_URL
        and settings.SUPABASE_SERVICE_ROLE_KEY
        and settings.SUPABASE_STORAGE_BUCKET
    )


def _process_image(uploaded_file) -> Image.Image:
    """Shared validation + processing, independent of where the result
    ends up being stored."""
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise AvatarUploadError("Image is too large (max 8MB).")

    content_type = getattr(uploaded_file, "content_type", None)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise AvatarUploadError(
            "That file type isn't supported. Please upload a JPEG, PNG, WEBP, or HEIC image."
        )

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
      - Supabase Storage when SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY /
        SUPABASE_STORAGE_BUCKET are all configured — this is REQUIRED for
        production. Django does not serve files from MEDIA_ROOT when
        DEBUG=False (see config/urls.py), so local-disk storage silently
        breaks every avatar upload in production: the file writes
        successfully, but the URL returned to the frontend 404s, which is
        exactly what a broken <img> in the app means.
      - Local disk (MEDIA_ROOT/avatars/) as a fallback when Supabase isn't
        configured, purely so local development doesn't require setting up
        a Supabase project just to test the avatar upload flow. Do not
        rely on this in production.

    Accepts whatever the browser sends from either a file picker ("choose
    from gallery") or `<input capture>` ("take a photo") — both arrive as
    the same multipart file upload from the frontend's point of view.
    """
    image = _process_image(uploaded_file)
    filename = f"{uuid.uuid4().hex}.jpg"

    if _supabase_configured():
        return _save_to_supabase(image, filename, old_avatar_path)

    logger.warning(
        "Supabase Storage is not configured — saving avatar to local disk. This WILL NOT "
        "work in production (Django doesn't serve MEDIA files when DEBUG=False). Set "
        "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_STORAGE_BUCKET before deploying."
    )
    return _save_to_local_disk(image, filename, old_avatar_path)


def _supabase_object_url(path: str) -> str:
    base = settings.SUPABASE_URL.rstrip("/")
    bucket = settings.SUPABASE_STORAGE_BUCKET
    return f"{base}/storage/v1/object/{bucket}/{path}"


def _supabase_public_url(path: str) -> str:
    base = settings.SUPABASE_URL.rstrip("/")
    bucket = settings.SUPABASE_STORAGE_BUCKET
    return f"{base}/storage/v1/object/public/{bucket}/{path}"


def _save_to_supabase(
    image: Image.Image, filename: str, old_avatar_path: str | None
) -> str:
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)
    buffer.seek(0)

    path = f"avatars/{filename}"

    try:
        resp = requests.post(
            _supabase_object_url(path),
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "image/jpeg",
                "x-upsert": "true",
                "Cache-Control": "31536000",
            },
            data=buffer.getvalue(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("Failed to upload avatar to Supabase Storage")
        raise AvatarUploadError(
            "Couldn't save the image right now — please try again."
        ) from exc

    public_base_prefix = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{settings.SUPABASE_STORAGE_BUCKET}/"

    # Clean up the previous uploaded avatar (only if it was one of ours —
    # never try to delete a Google/DiceBear URL, and skip anything that
    # isn't actually stored in this bucket, e.g. a leftover local-disk path
    # from before Supabase was configured).
    if old_avatar_path and old_avatar_path.startswith(public_base_prefix):
        old_path = old_avatar_path[len(public_base_prefix) :]
        try:
            requests.delete(
                _supabase_object_url(old_path),
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"
                },
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            logger.exception(
                "Failed to delete old avatar from Supabase Storage (non-fatal): %s",
                old_path,
            )

    return _supabase_public_url(path)


def _save_to_local_disk(
    image: Image.Image, filename: str, old_avatar_path: str | None
) -> str:
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
