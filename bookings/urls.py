from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, HostelInquiryViewSet

router = DefaultRouter()
router.register("inquiries", HostelInquiryViewSet, basename="inquiry")
router.register("", BookingViewSet, basename="booking")

urlpatterns = [
    path("", include(router.urls)),
]
