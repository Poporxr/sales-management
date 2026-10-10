"""Product photos, kept deliberately simple.

Photos live in assets/products/ as plain files. The database stores
only the filename, never the image data.

No thumbnail cache, no background loading: the catalog is small, so
images are loaded when a screen is built. If a file is missing or
broken, the product simply shows without a photo.
"""

import os
import shutil
import time

import customtkinter as ctk
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_DIR = os.path.join(BASE_DIR, "assets", "products")

# Pillow can open these; anything else is rejected at upload time.
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def ensure_folder():
    """Create the photo folder if it is not there yet."""
    os.makedirs(PRODUCTS_DIR, exist_ok=True)


def save_upload(source_path):
    """Copy a user-chosen image into assets/products/.

    Returns the stored filename. The name is based on the current time
    so two uploads can never overwrite each other.
    """
    ensure_folder()
    ext = os.path.splitext(source_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Please choose a PNG or JPG image.")
    filename = "product_%d%s" % (int(time.time() * 1000), ext)
    shutil.copyfile(source_path, os.path.join(PRODUCTS_DIR, filename))
    return filename


def photo_path(filename):
    """Full path for a stored filename, or None if there is none."""
    if not filename:
        return None
    path = os.path.join(PRODUCTS_DIR, filename)
    return path if os.path.isfile(path) else None


def thumbnail(filename, size=56):
    """A CustomTkinter image for a stored filename, or None.

    The caller must keep a reference to the returned object (for
    example as an attribute), or Tkinter will garbage-collect it and
    the photo will vanish.
    """
    path = photo_path(filename)
    if path is None:
        return None
    try:
        image = Image.open(path)
        return ctk.CTkImage(light_image=image, size=(size, size))
    except Exception:
        # Broken file: show no photo rather than crash the screen.
        return None
