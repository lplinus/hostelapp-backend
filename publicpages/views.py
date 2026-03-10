from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from .models import (
    HomePage,
    WhyUsItem,
    About,
    Contact,
    ContactMessage,
    Pricing,
    PricingPlan,
    PricingFeature,
    PricingFAQ,
    LandingPage,
)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    HomePageSerializer,
    WhyUsSerializer,
    AboutSerializer,
    ContactSerializer,
    ContactMessageSerializer,
    PricingSerializer,
    LandingPageSerializer,
)
from accounts.permissions import IsSuperAdmin
from rest_framework.generics import RetrieveAPIView
from rest_framework.generics import CreateAPIView


class HomePageAPIView(APIView):
    def get(self, request):
        homepage = HomePage.objects.first()
        serializer = HomePageSerializer(homepage)
        return Response(serializer.data)


class LandingPageAPIView(APIView):
    def get(self, request):
        landing_page = (
            LandingPage.objects.prefetch_related(
                "stats",
                "cities",
                "features",
                "steps",
                "testimonials",
            )
            .filter(is_active=True)
            .first()
        )

        if not landing_page:
            return Response({"error": "No active landing page found"}, status=404)

        serializer = LandingPageSerializer(landing_page)
        return Response(serializer.data)


# About us views=======================================================
class AboutAPIView(RetrieveAPIView):
    serializer_class = AboutSerializer

    def get_object(self):
        return About.objects.prefetch_related("stats", "values", "team_members").get(
            is_active=True
        )


class ContactAPIView(RetrieveAPIView):
    serializer_class = ContactSerializer

    def get_object(self):
        return get_object_or_404(
            Contact.objects.prefetch_related("info_items", "faqs"), is_active=True
        )


class ContactMessageAPIView(CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer


# Pricing plam views
class PricingAPIView(RetrieveAPIView):
    serializer_class = PricingSerializer

    def get_object(self):
        return get_object_or_404(
            Pricing.objects.prefetch_related(
                "plans__features",
                "faqs",
            ),
            is_active=True,
        )


# Admin views===============================================================starts-===========================
class AdminHomePageViewSet(viewsets.ModelViewSet):
    queryset = HomePage.objects.all()
    serializer_class = HomePageSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]


class AdminWhyUsViewSet(viewsets.ModelViewSet):
    queryset = WhyUsItem.objects.all()
    serializer_class = WhyUsSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]


# Admin views===============================================================ends-===========================
