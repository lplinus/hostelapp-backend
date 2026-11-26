import cloudinary.uploader
from concurrent.futures import ThreadPoolExecutor
from imagekitio import ImageKit
from django.conf import settings
import os
from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.base import ContentFile


class ImageUploadService:
    def __init__(self):
        # imagekitio 5.x initialization (Stainless based)
        # It only requires private_key. public_key and url_endpoint are not used in the constructor.
        self.ik_client = ImageKit(
            private_key=settings.IMAGEKIT_PRIVATE_KEY,
        )

    def _convert_to_webp(self, file_obj, quality=80, max_width=1920):
        """Helper to resize oversized images and convert to WebP in memory (zero local storage)."""
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

            img = Image.open(file_obj)
            img = ImageOps.exif_transpose(img)

            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = max(1, int(img.height * ratio))
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Convert to RGB if needed
            if img.mode in ("RGBA", "LA"):
                pass
            elif img.mode != "RGB":
                img = img.convert("RGB")

            buffer = BytesIO()
            img.save(buffer, format="WEBP", quality=quality, method=4)
            buffer.seek(0)
            return buffer
        except Exception:
            # Fallback to original if conversion fails
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            return file_obj

    def upload_image(self, file, file_name, folder="hostels"):
        """
        Uploads an image as WebP to the configured primary provider,
        with automatic fallback to the secondary provider.

        Primary/fallback is controlled by StorageSettings.image_storage_provider
        (configurable via Django Admin > CMS > Storage Settings):
          - 'imagekit'   -> ImageKit primary, Cloudinary fallback  (default)
          - 'cloudinary' -> Cloudinary primary, ImageKit fallback
        """
        # 1. Convert to WebP first (always — preserves existing conversion logic)
        processed_file = self._convert_to_webp(file)

        # Adjust filename to .webp
        name_without_ext = os.path.splitext(file_name)[0]
        webp_name = f"{name_without_ext}.webp"

        # Read active provider from DB (admin-configurable), fall back to settings/env
        from cms.models import StorageSettings
        active_provider = StorageSettings.get_active_provider()


        url = None
        provider = active_provider

        # ── IMAGEKIT PRIMARY ──────────────────────────────────────────────────
        if active_provider == "imagekit":
            # Testing flag to force ImageKit failure
            force_fail = getattr(settings, "FORCE_IMAGEKIT_FAILURE", False)

            if not force_fail:
                try:
                    if hasattr(processed_file, "seek"):
                        processed_file.seek(0)

                    upload_res = self.ik_client.files.upload(
                        file=processed_file.read(),
                        file_name=webp_name,
                        folder=folder,
                        use_unique_file_name=True,
                    )

                    if hasattr(upload_res, "url"):
                        url = upload_res.url
                    elif hasattr(upload_res, "response_metadata") and upload_res.response_metadata.raw:
                        url = upload_res.response_metadata.raw.get("url")
                except Exception:
                    # ImageKit failed -> fall through to Cloudinary
                    pass

            # Fallback to Cloudinary
            if not url:
                try:
                    if hasattr(processed_file, "seek"):
                        processed_file.seek(0)

                    cloudinary_res = cloudinary.uploader.upload(
                        processed_file,
                        folder=folder,
                        public_id=name_without_ext,
                        resource_type="image",
                        format="webp",
                    )
                    url = cloudinary_res.get("secure_url")
                    provider = "cloudinary"
                except Exception as e:
                    raise e

        # ── CLOUDINARY PRIMARY ────────────────────────────────────────────────
        elif active_provider == "cloudinary":
            try:
                if hasattr(processed_file, "seek"):
                    processed_file.seek(0)

                cloudinary_res = cloudinary.uploader.upload(
                    processed_file,
                    folder=folder,
                    public_id=name_without_ext,
                    resource_type="image",
                    format="webp",
                )
                url = cloudinary_res.get("secure_url")
            except Exception:
                # Cloudinary failed -> fall through to ImageKit
                pass

            # Fallback to ImageKit
            if not url:
                try:
                    if hasattr(processed_file, "seek"):
                        processed_file.seek(0)

                    upload_res = self.ik_client.files.upload(
                        file=processed_file.read(),
                        file_name=webp_name,
                        folder=folder,
                        use_unique_file_name=True,
                    )

                    if hasattr(upload_res, "url"):
                        url = upload_res.url
                    elif hasattr(upload_res, "response_metadata") and upload_res.response_metadata.raw:
                        url = upload_res.response_metadata.raw.get("url")
                    provider = "imagekit"
                except Exception as e:
                    raise e

        else:
            raise ValueError(
                f"Unknown IMAGE_STORAGE_PROVIDER: '{active_provider}'. "
                f"Valid options are 'imagekit' or 'cloudinary'."
            )

        return {
            "url": url,
            "provider": provider,
        }

    def upload_images_batch(self, items, folder="hostels", max_workers=5):
        """
        Concurrently compress (in-memory WebP) and upload multiple (file_obj, file_name) tuples
        to the active third-party storage provider without touching local disk.
        """
        if not items:
            return []

        def _upload_one(pair):
            file_obj, file_name = pair
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            raw_bytes = file_obj.read()
            mem_buf = BytesIO(raw_bytes)
            return self.upload_image(mem_buf, file_name, folder=folder)

        workers = min(max_workers, len(items))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(_upload_one, items))
