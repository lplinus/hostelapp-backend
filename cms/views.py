"""
Views for the CMS (Content Management System) application.
Provides endpoints for retrieving legal documents (Terms, Privacy Policy),
FAQs, and general storage settings.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from cms.serializers import TermsSerializer, PrivacyPolicySerializer, FAQCategorySerializer, FAQSerializer, StorageSettingsSerializer
from cms.services import TermsService, PrivacyPolicyService, FAQCategoryService, FAQService
from .models import StorageSettings


class StorageSettingsView(APIView):
    """
    Retrieves global storage settings (e.g., base URLs for media/static files).
    """
    def get(self, request):
        settings_obj, created = StorageSettings.objects.get_or_create(pk=1)
        serializer = StorageSettingsSerializer(settings_obj)
        return Response(serializer.data)



class TermsView(APIView):
    """
    Retrieves the latest Terms and Conditions content.
    """

    def get(self, request):
        terms = TermsService.get_terms()

        if not terms:
            return Response(
                {"detail": "Terms not available"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TermsSerializer(terms)
        return Response(serializer.data)



class PrivacyPolicyView(APIView):
    """
    Retrieves the latest Privacy Policy content.
    """

    def get(self, request):
        privacy_policy = PrivacyPolicyService.get_privacy_policy()

        if not privacy_policy:
            return Response(
                {"detail": "Privacy policy not available"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PrivacyPolicySerializer(privacy_policy)
        return Response(serializer.data)

class FAQCategoryListView(APIView):
    """
    Lists all available FAQ categories (used for grouping FAQs).
    """

    def get(self, request):
        categories = FAQCategoryService.get_faq_categories()
        serializer = FAQCategorySerializer(categories, many=True)
        return Response(serializer.data)

class FAQListView(APIView):
    """
    Lists all FAQs, optionally filtered by a category ID.
    Used for the main FAQ page.
    """

    def get(self, request):
        category_id = request.query_params.get('category', None)
        faqs = FAQService.get_faqs(category_id=category_id)
        serializer = FAQSerializer(faqs, many=True)
        return Response(serializer.data)

class FAQSearchView(APIView):
    """
    Search endpoint for FAQs based on a search query 'q'.
    """

    def get(self, request):
        query = request.query_params.get('q', '')
        faqs = FAQService.search_faqs(query)
        serializer = FAQSerializer(faqs, many=True)
        return Response(serializer.data)

class FAQDetailView(APIView):
    """
    Retrieves details of a specific FAQ by its slug.
    Also increments the view count for analytics.
    """

    def get(self, request, slug):
        faq = FAQService.get_faq(slug)
        if not faq:
            return Response(
                {"detail": "FAQ not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        FAQService.increment_view_count(faq)
        serializer = FAQSerializer(faq)
        return Response(serializer.data)


class UploadSignatureView(APIView):
    """
    Returns a short-lived signed upload token for direct browser-to-cloud uploads
    (ImageKit or Cloudinary based on StorageSettings.get_active_provider()),
    along with the active max_image_size_mb limit.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        import hashlib
        import hmac
        import time
        import uuid
        import cloudinary.utils
        from django.conf import settings
        from .models import StorageSettings

        settings_obj = StorageSettings.objects.get_or_create(pk=1)[0]
        provider = StorageSettings.get_active_provider()
        raw_folder = (request.query_params.get("folder") or "uploads").strip("/")
        folder = "".join(c for c in raw_folder if c.isalnum() or c in ("/", "-", "_")) or "uploads"

        base_payload = {
            "provider": provider,
            "folder": folder,
            "max_image_size_mb": settings_obj.max_image_size_mb,
        }

        if provider == StorageSettings.PROVIDER_CLOUDINARY:
            timestamp = int(time.time())
            sign_params = {
                "timestamp": timestamp,
                "folder": folder,
                "allowed_formats": "webp,jpg,jpeg,png,gif",
            }
            signature = cloudinary.utils.api_sign_request(
                sign_params,
                settings.CLOUDINARY_API_SECRET,
            )
            return Response({
                **base_payload,
                "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
                "api_key": settings.CLOUDINARY_API_KEY,
                "timestamp": timestamp,
                "allowed_formats": "webp,jpg,jpeg,png,gif",
                "signature": signature,
            })

        token = str(uuid.uuid4())
        expire = int(time.time()) + 600
        signature = hmac.new(
            settings.IMAGEKIT_PRIVATE_KEY.encode("utf-8"),
            f"{token}{expire}".encode("utf-8"),
            hashlib.sha1,
        ).hexdigest()
        return Response({
            **base_payload,
            "public_key": settings.IMAGEKIT_PUBLIC_KEY,
            "url_endpoint": settings.IMAGEKIT_URL_ENDPOINT,
            "token": token,
            "expire": expire,
            "signature": signature,
        })