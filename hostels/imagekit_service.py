from imagekitio import ImageKit
from django.conf import settings
from typing import Dict


class ImageKitService:
    def __init__(self):
        self.client = ImageKit(
            private_key=settings.IMAGEKIT_PRIVATE_KEY,
        )

    def upload(self, file, file_name: str, folder: str = "/") -> Dict:
        result = self.client.files.upload(
            file=file.read() if hasattr(file, 'read') else file,
            file_name=file_name,
            folder=folder,
        )

        return {
            "url": result.response_metadata.raw.get("url"),
            "file_id": result.response_metadata.raw.get("fileId"),
        }