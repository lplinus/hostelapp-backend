"""
Utility to convert any uploaded image to WebP format.
Works with Django ImageField. Supports JPEG, PNG, BMP, TIFF, AVIF, etc.
"""

import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile


def convert_to_webp(image_field, quality=80):
    """
    Convert an ImageField's file to WebP format.

    Args:
        image_field: A Django ImageField instance (e.g. instance.image)
        quality: WebP compression quality (1-100, default 80)

    Returns:
        None if already WebP or no image, otherwise updates the field in-place.
    """
    if not image_field or not image_field.name:
        return None

    # Skip if already WebP
    name_lower = image_field.name.lower()
    if name_lower.endswith(".webp"):
        return None

    try:
        image_field.open()
        img = Image.open(image_field)

        # Convert to RGB if needed (e.g. RGBA PNGs, palette images)
        if img.mode in ("RGBA", "LA"):
            # Preserve transparency
            pass
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Save as WebP into memory
        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=quality)
        buffer.seek(0)

        # Build new filename with .webp extension
        old_name = image_field.name
        base_name = os.path.splitext(os.path.basename(old_name))[0]
        upload_to = os.path.dirname(old_name)
        new_name = os.path.join(upload_to, f"{base_name}.webp")

        # Replace the file content
        image_field.save(new_name, ContentFile(buffer.read()), save=False)

        return new_name
    except Exception:
        # If conversion fails, keep the original
        return None


def process_image_fields(instance, field_names, quality=80):
    """
    Process multiple image fields on a model instance, converting each to WebP.

    Args:
        instance: Django model instance
        field_names: List of field names to process (e.g. ["image", "image2"])
        quality: WebP compression quality

    Returns:
        True if any field was converted, False otherwise.
    """
    converted = False
    for field_name in field_names:
        field = getattr(instance, field_name, None)
        if field and field.name and not field.name.lower().endswith(".webp"):
            result = convert_to_webp(field, quality=quality)
            if result is not None:
                converted = True
    return converted
