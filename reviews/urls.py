from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # ReviewViewSet,  # Commented out - platform focuses on hotels and vacation rentals
    HotelReviewViewSet,
    VacationRentalReviewViewSet,
)

router = DefaultRouter()
router.register("hotels", HotelReviewViewSet, basename="hotel-review")
router.register("vacation-rentals", VacationRentalReviewViewSet, basename="vacation-rental-review")
# router.register("", ReviewViewSet, basename="review")  # Hostel reviews commented out

urlpatterns = [
    path("", include(router.urls)),
]
