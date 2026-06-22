import os
import uuid

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC uploads (common from iPhone cameras) will fail validation instead of crashing.

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB — generous for a phone camera photo
TARGET_SIZE = 512  # square thumbnail, plenty for any avatar display size
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


class AvatarUploadError(Exception):
    pass


def save_avatar(user_id: str, uploaded_file, old_avatar_path: str | None) -> str:
    """
    Validates and processes an uploaded avatar image, saves it to
    MEDIA_ROOT/avatars/, and returns the path to store on User.avatar
    (relative to MEDIA_ROOT, e.g. "avatars/<uuid>.jpg").

    Accepts whatever the browser sends from either a file picker ("choose
    from gallery") or `<input capture>` ("take a photo") — both arrive as
    the same multipart file upload from the frontend's point of view; the
    distinction is purely in how the browser/OS prompts the user, not in
    what reaches this endpoint.
    """
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
    image = image.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)

    avatars_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
    os.makedirs(avatars_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.jpg"
    full_path = os.path.join(avatars_dir, filename)
    image.save(full_path, "JPEG", quality=88)

    # Clean up the previous uploaded avatar (only if it was one of ours —
    # never try to delete a Google/DiceBear URL).
    if old_avatar_path and not old_avatar_path.startswith("http"):
        old_full_path = os.path.join(settings.MEDIA_ROOT, old_avatar_path)
        if os.path.exists(old_full_path):
            try:
                os.remove(old_full_path)
            except OSError:
                pass

    return f"avatars/{filename}"
