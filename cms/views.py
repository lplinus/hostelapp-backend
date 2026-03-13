from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TermsSerializer, PrivacyPolicySerializer,FAQCategorySerializer,FAQSerializer
from .services import TermsService, PrivacyPolicyService,FAQCategoryService,FAQService


class TermsView(APIView):

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

    def get(self, request):
        categories = FAQCategoryService.get_faq_categories()
        serializer = FAQCategorySerializer(categories, many=True)
        return Response(serializer.data)

class FAQListView(APIView):

    def get(self, request):
        faqs = FAQService.get_faqs()
        serializer = FAQSerializer(faqs, many=True)
        return Response(serializer.data)

class FAQDetailView(APIView):

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