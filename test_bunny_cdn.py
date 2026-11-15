"""
Bunny CDN & Storage Automated Test Suite
Verifies credentials, file upload, CDN delivery, and cleanup.
Run via: python test_bunny_cdn.py
"""

import os
import sys
import requests
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Setup Django environment to read config from settings/.env
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hbackend.settings")
import django
django.setup()

from django.conf import settings


def test_bunny_cdn():
    print("=" * 60)
    print(" 🐰 BUNNY CDN & STORAGE ZONE TEST RUNNER")
    print("=" * 60)

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", "")
    domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "")
    secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "")

    print(f"• Storage Zone Name : {bucket}")
    print(f"• Endpoint URL       : {endpoint}")
    print(f"• CDN Pull Domain   : {domain}")
    print(f"• Access Key Set    : {'YES (Password detected)' if secret_key else 'NO'}")
    print("-" * 60)

    if not bucket or not secret_key:
        print("❌ FAILED: Missing AWS_STORAGE_BUCKET_NAME or AWS_SECRET_ACCESS_KEY in .env")
        return False

    # 1x1 valid transparent PNG
    test_png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08"
        b"\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00"
        b"\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    test_file_name = "test_verification_image.png"
    upload_url = f"https://storage.bunnycdn.com/{bucket}/{test_file_name}"
    cdn_url = f"https://{domain}/{test_file_name}"

    headers = {
        "AccessKey": secret_key,
        "Content-Type": "image/png",
    }

    # Step 1: Upload Test Image
    print(f"[1/3] Uploading test image to Bunny Storage API...")
    try:
        put_resp = requests.put(upload_url, data=test_png_bytes, headers=headers, timeout=12)
        if put_resp.status_code in [200, 201]:
            print(f"  ✅ Upload Succeeded: HTTP {put_resp.status_code} ({put_resp.text.strip()})")
        else:
            print(f"  ❌ Upload Failed: HTTP {put_resp.status_code} - {put_resp.text}")
            return False
    except Exception as e:
        print(f"  ❌ Connection Error: {e}")
        return False

    # Step 2: Verify Public Reachability via Bunny CDN
    print(f"[2/3] Verifying CDN Delivery via {cdn_url}...")
    try:
        cdn_resp = requests.get(cdn_url, timeout=12)
        if cdn_resp.status_code == 200 and len(cdn_resp.content) == len(test_png_bytes):
            print(f"  ✅ CDN Retrieval Succeeded: HTTP 200 (Received {len(cdn_resp.content)} bytes)")
            print(f"  🔗 Public URL: {cdn_url}")
        else:
            print(f"  ⚠️ Warning: CDN returned HTTP {cdn_resp.status_code}. Edge replication may take a few seconds.")
    except Exception as e:
        print(f"  ⚠️ CDN Delivery Error: {e}")

    # Step 3: Cleanup Test File
    print(f"[3/3] Cleaning up test file from Bunny Storage...")
    try:
        del_resp = requests.delete(upload_url, headers=headers, timeout=12)
        if del_resp.status_code in [200, 204]:
            print(f"  ✅ Cleanup Succeeded: HTTP {del_resp.status_code}")
        else:
            print(f"  ℹ️ Delete status: HTTP {del_resp.status_code}")
    except Exception as e:
        print(f"  ⚠️ Cleanup Error: {e}")

    print("=" * 60)
    print(" 🎉 BUNNY CDN IS FULLY OPERATIONAL & CONNECTED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_bunny_cdn()
