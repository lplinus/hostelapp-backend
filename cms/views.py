"""
Views for the CMS (Content Management System) application.
Provides endpoints for retrieving legal documents (Terms, Privacy Policy),
FAQs, and general storage settings.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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