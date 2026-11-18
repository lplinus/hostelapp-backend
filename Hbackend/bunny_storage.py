import os
import mimetypes
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

# Persistent HTTP session with keep-alive connection pooling
_bunny_session = requests.Session()
_adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=Retry(total=2, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
)
_bunny_session.mount("https://", _adapter)
_bunny_session.mount("http://", _adapter)


@deconstructible
class BunnyCDNStorage(Storage):
    """
    Custom Storage backend for Bunny CDN & Bunny Storage Zone.
    Uploads verification documents directly to Bunny Storage API
    and serves them securely via Bunny CDN pull domain.
    """
    def __init__(self, **kwargs):
        self.bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "hotel-hostel-vacanatinaldb")
        self.domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "hotelcdn.b-cdn.net")
        self.api_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
        self.base_storage_url = f"https://storage.bunnycdn.com/{self.bucket}"

    def _save(self, name, content):
        clean_name = name.replace("\\", "/").lstrip("/")
        upload_url = f"{self.base_storage_url}/{clean_name}"

        content_type = getattr(content, "content_type", None)
        if not content_type:
            content_type, _ = mimetypes.guess_type(clean_name)
        if not content_type:
            content_type = "application/octet-stream"

        headers = {
            "AccessKey": self.api_key,
            "Content-Type": content_type,
        }

        if hasattr(content, "seek"):
            content.seek(0)
        data = content.read() if hasattr(content, "read") else content

        response = _bunny_session.put(upload_url, data=data, headers=headers, timeout=30)
        if response.status_code not in (200, 201):
            raise IOError(f"Bunny CDN Upload Failed: HTTP {response.status_code} - {response.text}")

        return clean_name

    def url(self, name):
        if not name:
            return ""
        if name.startswith("http://") or name.startswith("https://"):
            return name
        clean_name = name.replace("\\", "/").lstrip("/")
        return f"https://{self.domain}/{clean_name}"

    def exists(self, name):
        return False

    def size(self, name):
        """
        Returns file size in bytes from Bunny Storage.
        """
        if not name:
            return 0
        clean_name = name.replace("\\", "/").lstrip("/")
        headers = {"AccessKey": self.api_key}
        try:
            r = _bunny_session.head(f"{self.base_storage_url}/{clean_name}", headers=headers, timeout=5)
            if r.status_code == 200:
                return int(r.headers.get("Content-Length", 0))
        except Exception:
            pass
        return 0

    def delete(self, name):
        """
        Deletes the file permanently from Bunny Storage Zone.
        """
        if not name:
            return True
        clean_name = name.replace("\\", "/").lstrip("/")
        delete_url = f"{self.base_storage_url}/{clean_name}"
        headers = {"AccessKey": self.api_key}
        try:
            res = _bunny_session.delete(delete_url, headers=headers, timeout=10)
            return res.status_code in (200, 204, 404)
        except Exception:
            return False


bunny_storage = BunnyCDNStorage()
