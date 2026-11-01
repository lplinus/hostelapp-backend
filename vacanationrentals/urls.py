from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VacationRentalViewSet,
    VacationRentalAvailabilityViewSet,
    VacationRentalBookingViewSet,
)

app_name = "vacanationrentals"

router = DefaultRouter()
router.register("properties", VacationRentalViewSet, basename="vacation-rental")
router.register("availability", VacationRentalAvailabilityViewSet, basename="vacation-rental-availability")
router.register("bookings", VacationRentalBookingViewSet, basename="vacation-rental-booking")

# Allow direct root mappings like /api/vacanationrentals/
rental_list = VacationRentalViewSet.as_view({"get": "list", "post": "create"})
rental_detail = VacationRentalViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"})

urlpatterns = [
    path("", include(router.urls)),
    path("", rental_list, name="vacation-rental-root-list"),
    path("<slug:slug>/", rental_detail, name="vacation-rental-root-detail"),
]
