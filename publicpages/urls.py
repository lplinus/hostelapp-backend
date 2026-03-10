from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    HomePageAPIView,
    LandingPageAPIView,
    AdminHomePageViewSet,
    AdminWhyUsViewSet,
    ContactMessageAPIView,
    PricingAPIView,
    AboutAPIView,
    ContactAPIView,
)

# 🔹 Public API
urlpatterns = [
    path("homepage/", HomePageAPIView.as_view(), name="homepage"),
    path("landingpage/", LandingPageAPIView.as_view(), name="landingpage"),
    path("about/", AboutAPIView.as_view(), name="about-api"),
    path("contact/", ContactAPIView.as_view(), name="contact-api"),
    path(
        "contact/message/", ContactMessageAPIView.as_view(), name="contact-message-api"
    ),
    path("pricing/", PricingAPIView.as_view(), name="pricing-api"),
]


# 🔹 Admin Router
router = DefaultRouter()
router.register("admin/homepage", AdminHomePageViewSet, basename="admin-homepage")
router.register("admin/whyus", AdminWhyUsViewSet, basename="admin-whyus")

# 🔹 Combine both
urlpatterns += router.urls
