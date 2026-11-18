from django.urls import path
from .views import (
    CurrentGuestProfileView,
    GuestDocumentsView,
    GuestDocumentDetailView,
    GuestBookingsListView,
    StaffVerifyGuestDocView,
)

app_name = "guestprofile"

urlpatterns = [
    path("me/", CurrentGuestProfileView.as_view(), name="guest-profile-me"),
    path("documents/", GuestDocumentsView.as_view(), name="guest-documents-list"),
    path("documents/<uuid:pk>/", GuestDocumentDetailView.as_view(), name="guest-document-detail"),
    path("bookings/", GuestBookingsListView.as_view(), name="guest-bookings-list"),
    path("verify-document/<str:booking_ref>/", StaffVerifyGuestDocView.as_view(), name="staff-verify-document"),
]
