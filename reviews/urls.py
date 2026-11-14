from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReviewViewSet,
    HotelReviewViewSet,
    VacationRentalReviewViewSet,
)

router = DefaultRouter()
router.register("hotels", HotelReviewViewSet, basename="hotel-review")
router.register("vacation-rentals", VacationRentalReviewViewSet, basename="vacation-rental-review")
router.register("", ReviewViewSet, basename="review")

urlpatterns = [
    path("", include(router.urls)),
]
