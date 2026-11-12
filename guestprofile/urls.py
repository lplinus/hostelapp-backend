from django.urls import path
from .views import (
    CurrentGuestProfileView,
    GuestBookingsListView,
    StaffVerifyGuestDocView,
)

app_name = "guestprofile"

urlpatterns = [
    path("me/", CurrentGuestProfileView.as_view(), name="guest-profile-me"),
    path("bookings/", GuestBookingsListView.as_view(), name="guest-bookings-list"),
    path("verify-document/<str:booking_ref>/", StaffVerifyGuestDocView.as_view(), name="staff-verify-document"),
]
