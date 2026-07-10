# ==============================================================================
# File:      api/app/utils/uploads.py
# Purpose:   File upload utilities. Handles avatar image processing (resize
#            to multiple sizes), saving to disk, and deletion. Validates file
#            type and size.
# Callers:   routes/uploads.py
# Callees:   os, uuid, logging, PIL (Pillow), werkzeug.utils
# Modified:  2026-06-01
# ==============================================================================
import os
import uuid
import logging
from PIL import Image
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_SIZES = {
    'sm': (64, 64),
    'md': (256, 256),
}
def _ensure_dirs():
    for subdir in ['avatars']:
        path = os.path.join(UPLOAD_DIR, subdir)
        os.makedirs(path, exist_ok=True)


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _strip_exif(image):
    """Strip EXIF metadata by creating a clean copy from pixel data."""
    clean = Image.new(image.mode, image.size)
    clean.putdata(list(image.getdata()))
    return clean


def _resize_and_save(image, base_path, sizes):
    """Resize image to multiple sizes and save. Returns the base filename (without size suffix)."""
    image = _strip_exif(image)
    saved = {}
    for label, (w, h) in sizes.items():
        resized = image.copy()
        resized.thumbnail((w, h), Image.LANCZOS)
        out_path = f"{base_path}_{label}.jpg"
        resized = resized.convert('RGB')
        resized.save(out_path, 'JPEG', quality=85)
        saved[label] = os.path.basename(out_path)
    return saved


def save_avatar(file_storage):
    """Process and save an avatar upload. Returns base filename or (None, error)."""
    _ensure_dirs()

    if not file_storage or not file_storage.filename:
        return None, 'No file provided'

    if not _allowed_file(file_storage.filename):
        return None, 'Only JPG and PNG files are allowed'

    # Check size
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_FILE_SIZE:
        return None, f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB'

    try:
        img = Image.open(file_storage)
        base_name = f"{uuid.uuid4().hex}"
        base_path = os.path.join(UPLOAD_DIR, 'avatars', base_name)
        _resize_and_save(img, base_path, AVATAR_SIZES)
        return base_name, None
    except Exception as e:
        logger.error(f"Avatar upload failed: {e}")
        return None, 'Failed to process image'


def delete_avatar(base_name):
    """Delete avatar files."""
    if not base_name:
        return
    for label in AVATAR_SIZES:
        path = os.path.join(UPLOAD_DIR, 'avatars', f"{base_name}_{label}.jpg")
        if os.path.exists(path):
            os.remove(path)


def get_upload_url(subdir, base_name, size='md'):
    """Get the URL path for an upload."""
    if not base_name:
        return None
    return f"/api/uploads/{subdir}/{base_name}_{size}.jpg"
