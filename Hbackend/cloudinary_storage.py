import os
from io import BytesIO
from PIL import Image
from django.core.files.storage import Storage
from django.conf import settings
from django.core.files.base import ContentFile
import cloudinary
import cloudinary.uploader
import cloudinary.api


class CloudinaryStorage(Storage):
    """
    Custom Django Storage backend that uploads files to Cloudinary.
    - Converts image files to WebP before uploading (mirrors ImageKitStorage).
    - Used as the global 'default' storage when IMAGE_STORAGE_PROVIDER='cloudinary'.
    """

    def _save(self, name, content):
        # Normalize path separators
        name = name.replace("\\", "/")

        ext = os.path.splitext(name)[1].lower()
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".jfif", ".avif"]

        if ext in image_extensions:
            try:
                # Open & convert to WebP
                img = Image.open(content)

                if img.mode in ("RGBA", "LA"):
                    pass  # Preserve transparency
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                buffer = BytesIO()
                img.save(buffer, format="WEBP", quality=80)
                buffer.seek(0)

                content = ContentFile(buffer.read())
                name = os.path.splitext(name)[0] + ".webp"
            except Exception as e:
                print(f"DEBUG CloudinaryStorage: WebP conversion failed: {e}")
                if hasattr(content, "seek"):
                    content.seek(0)

        # Determine folder and public_id from name
        folder = os.path.dirname(name)
        basename = os.path.basename(name)
        # Remove .webp extension for public_id (Cloudinary appends it automatically)
        public_id_base = os.path.splitext(basename)[0]
        public_id = f"{folder}/{public_id_base}" if folder else public_id_base

        content.seek(0)

        res = cloudinary.uploader.upload(
            content.read(),
            folder=folder if folder else None,
            public_id=public_id_base,
            resource_type="image",
            format="webp",
            overwrite=False,
            unique_filename=True,
        )

        # Return the secure URL so Django stores it as the file name
        return res.get("secure_url", name)

    def url(self, name):
        # If name is already a full Cloudinary URL, return it as-is
        if name and name.startswith("http"):
            return name
        # Fallback: build a Cloudinary URL manually
        cloud_name = settings.CLOUDINARY_CLOUD_NAME if hasattr(settings, "CLOUDINARY_CLOUD_NAME") else ""
        return f"https://res.cloudinary.com/{cloud_name}/image/upload/{name}"

    def exists(self, name):
        return False

    def get_available_name(self, name, max_length=None):
        return name

    def size(self, name):
        """
        Return 0 to avoid NotImplementedError in Django Admin.
        Actual size checking is handled by validate_image_size before upload.
        """
        return 0

    def delete(self, name):
        """
        Delete from Cloudinary using the stored URL or public_id.
        """
        if not name:
            return

        try:
            # If it's a full URL, extract the public_id
            if name.startswith("http"):
                # Example URL: https://res.cloudinary.com/<cloud>/image/upload/v123/<folder>/<public_id>.webp
                # We need everything after '/upload/' stripping the version prefix (v\d+/)
                upload_marker = "/upload/"
                idx = name.find(upload_marker)
                if idx == -1:
                    return
                after_upload = name[idx + len(upload_marker):]
                # Strip version component (e.g., "v1712345678/")
                parts = after_upload.split("/")
                if parts and parts[0].startswith("v") and parts[0][1:].isdigit():
                    parts = parts[1:]
                # Remove file extension for public_id
                public_id_with_ext = "/".join(parts)
                public_id = os.path.splitext(public_id_with_ext)[0]
            else:
                public_id = os.path.splitext(name)[0]

            cloudinary.api.delete_resources([public_id], resource_type="image")
            print(f"DEBUG CloudinaryStorage: Deleted {public_id} from Cloudinary")
        except Exception as e:
            print(f"DEBUG CloudinaryStorage: Delete failed for {name}: {e}")
