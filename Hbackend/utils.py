"""
Utility to convert any uploaded image to WebP format.
Works with Django ImageField. Supports JPEG, PNG, BMP, TIFF, AVIF, etc.
"""

import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError


def validate_image_size(image_field):
    """
    Validate that the uploaded image size is within the limit set in StorageSettings.
    """
    try:
        from cms.models import StorageSettings
        settings_obj = StorageSettings.objects.get_or_create(pk=1)[0]
        max_size_mb = settings_obj.max_image_size_mb
    except Exception:
        # Fallback to 10MB if something goes wrong
        max_size_mb = 10
    
    if image_field and hasattr(image_field, 'size'):
        if image_field.size > max_size_mb * 1024 * 1024:
            raise ValidationError(f"Image file too large. Max size is {max_size_mb} MB.")



def convert_to_webp(image_field, quality=80):
    """
    Convert an ImageField's file to WebP format.

    Args:
        image_field: A Django ImageField instance (e.g. instance.image)
        quality: WebP compression quality (1-100, default 80)

    Returns:
        None if already WebP or no image, otherwise updates the field in-place.
    """
    # Skip if it's a full URL (already in ImageKit)
    if image_field.name.startswith('http'):
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
        old_path = image_field.path if hasattr(image_field, 'path') and image_field.path else None
        
        base_name = os.path.splitext(os.path.basename(old_name))[0]
        upload_to = os.path.dirname(old_name)
        new_name = os.path.join(upload_to, f"{base_name}.webp")

        # Replace the file content
        image_field.save(new_name, ContentFile(buffer.read()), save=False)

        # Delete original file if it exists locally and wasn't already a webp
        if old_path:
            try:
                if os.path.exists(old_path) and not old_path.lower().endswith('.webp'):
                    os.remove(old_path)
            except (NotImplementedError, Exception) as e:
                print(f"DEBUG: Failed to delete old file: {e}")

        print(f"DEBUG: Successfully converted to WebP: {new_name}")
        return new_name
    except Exception as e:
        print(f"DEBUG: WebP conversion failed for {getattr(image_field, 'name', 'unknown')}: {e}")
        # If conversion fails, keep the original
        return None


def delete_old_image_files(instance, field_names):
    """
    Delete old files from storage when they are replaced by new ones.
    Call this BEFORE process_image_fields or super().save().
    """
    if not instance.pk:
        return
    try:
        # Get the current version of the instance from the database
        model = instance.__class__
        old_instance = model.all_objects.filter(pk=instance.pk).first()
        if not old_instance:
            return

        for field_name in field_names:
            old_file = getattr(old_instance, field_name, None)
            new_file = getattr(instance, field_name, None)
            
            # If the file has changed and old one exists, delete it
            if old_file and old_file.name and old_file.name != getattr(new_file, 'name', None):
                # Try to use storage.delete if available
                try:
                    instance._meta.get_field(field_name).storage.delete(old_file.name)
                except Exception:
                    # Fallback to os.remove if it's a local path
                    if hasattr(old_file, 'path'):
                        try:
                            if os.path.exists(old_file.path):
                                os.remove(old_file.path)
                        except (NotImplementedError, Exception):
                            pass
    except Exception:
        pass


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
