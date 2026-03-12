from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TermsSerializer, PrivacyPolicySerializer
from .services import TermsService, PrivacyPolicyService


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