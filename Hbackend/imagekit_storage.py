import os
from io import BytesIO
from PIL import Image
from django.core.files.storage import Storage
from django.conf import settings
from imagekitio import ImageKit
from django.core.files.base import ContentFile


class ImageKitStorage(Storage):
    def __init__(self):
        # imagekitio 5.x initialization (Stainless based)
        # It only requires private_key. public_key and url_endpoint are not used in the constructor.
        self.client = ImageKit(
            private_key=settings.IMAGEKIT_PRIVATE_KEY,
        )

    def _save(self, name, content):
        # Normalize path
        name = name.replace("\\", "/")

        # Determine if it's an image that needs conversion
        ext = os.path.splitext(name)[1].lower()
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".jfif", ".avif"]

        if ext in image_extensions:
            try:
                # Open image and convert to WebP
                img = Image.open(content)

                # Convert to RGB if needed
                if img.mode in ("RGBA", "LA"):
                    pass
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Downscale ultra-high resolution images (> 2560px) to prevent exceeding ImageKit 25MP limit
                max_dim = 2560
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                buffer = BytesIO()
                img.save(buffer, format="WEBP", quality=80)
                buffer.seek(0)

                # Update content and name
                content = ContentFile(buffer.read())
                name = os.path.splitext(name)[0] + ".webp"
            except Exception as e:
                # If conversion fails, proceed with original
                print(f"DEBUG: Storage conversion failed: {e}")
                if hasattr(content, "seek"):
                    content.seek(0)

        folder = os.path.dirname(name)
        filename = os.path.basename(name)

        # Ensure we are at the start of the file
        content.seek(0)

        # Upload to ImageKit
        res = self.client.files.upload(
            file=content.read(),
            file_name=filename,
            folder=folder if folder else "/",
            use_unique_file_name=True,
        )

        if hasattr(res, "url"):
            return res.url

        return name

    def url(self, name):
        # If name is already a full URL, return it
        if name.startswith("http"):
            return name
        # Otherwise, prepend endpoint
        return f"{settings.IMAGEKIT_URL_ENDPOINT.rstrip('/')}/{name.lstrip('/')}"

    def exists(self, name):
        return False

    def get_available_name(self, name, max_length=None):
        return name

    def size(self, name):
        """
        Return the size of the file in bytes.
        Since we are using ImageKit, fetching this exactly would require an API call.
        Returning 0 for now to avoid NotImplementedError in Django Admin.
        In validate_image_size, it checks the uploaded file size before it's saved.
        """
        return 0

    def delete(self, name):
        """
        Delete from ImageKit using the name/URL.
        """
        if not name:
            return

        try:
            # Strip query params if any
            clean_name = str(name).split("?")[0].strip()
            endpoint = settings.IMAGEKIT_URL_ENDPOINT.rstrip("/")

            if clean_name.startswith("http"):
                if clean_name.startswith(endpoint):
                    path_val = clean_name[len(endpoint) :].lstrip("/")
                else:
                    from urllib.parse import urlparse
                    parsed = urlparse(clean_name)
                    path_parts = parsed.path.strip("/").split("/")
                    endpoint_id = endpoint.split("/")[-1]
                    if path_parts and path_parts[0] == endpoint_id:
                        path_parts = path_parts[1:]
                    path_val = "/".join(path_parts)
            else:
                path_val = clean_name.lstrip("/")

            filename = os.path.basename(path_val)
            folder = os.path.dirname(path_val)
            if not folder.startswith("/"):
                folder = "/" + folder

            # Search using client.assets.list in imagekitio 5.x
            matched_files = []
            try:
                matched_files = list(self.client.assets.list(search_query=f'name="{filename}"'))
            except Exception:
                try:
                    matched_files = list(self.client.assets.list(path=folder if folder else "/"))
                except Exception:
                    pass

            for file in matched_files:
                f_name = getattr(file, "name", None)
                f_id = getattr(file, "file_id", None)
                if f_name == filename and f_id:
                    self.client.files.delete(f_id)
                    print(
                        f"DEBUG: Deleted file {path_val} (ID: {f_id}) from ImageKit"
                    )
                    return
        except Exception as e:
            print(f"DEBUG: ImageKit delete failed for {name}: {e}")

