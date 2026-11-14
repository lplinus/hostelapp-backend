"""
Views for the Reviews application.
Allows users to post reviews for hostels, hotels, and vacation rentals.
Includes logic for moderation (auto-approval settings), verified booking attachment,
and ownership verification.
"""
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Review, HotelReview, VacationRentalReview
from .serializers import (
    ReviewSerializer,
    HotelReviewSerializer,
    VacationRentalReviewSerializer,
)


class IsReviewOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to ensure only the review author can edit/delete it.
    Read-only for everyone, write for authenticated users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class BaseReviewViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet providing common moderation and ownership verification
    for hostel, hotel, and vacation rental reviews.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsReviewOwnerOrReadOnly]
    pagination_class = None

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [p() for p in self.permission_classes]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        booking = serializer.validated_data.get("booking")

        # Verified booking checks
        if booking:
            booking_user = getattr(booking, "user", None)
            if booking_user and user and booking_user != user and not self.request.user.is_staff:
                raise PermissionDenied("You can only submit reviews for your own bookings.")
            if not user and booking_user:
                user = booking_user
            # Verified bookings are auto-approved
            is_approved = True
        else:
            is_approved = getattr(settings, "REVIEWS_AUTO_APPROVE", False)

        publish_delay = getattr(settings, "REVIEWS_PUBLISH_DELAY", 0)
        published_at = timezone.now() + timedelta(seconds=publish_delay)

        # Auto-populate name if empty and user is logged in
        name = serializer.validated_data.get("name")
        if not name and user:
            name = f"{user.first_name} {user.last_name}".strip() or user.username

        serializer.save(
            user=user,
            name=name,
            is_approved=is_approved,
            published_at=published_at,
        )

    def perform_update(self, serializer):
        obj = serializer.instance
        if obj.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only edit your own reviews.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only delete your own reviews.")
        instance.delete()


class ReviewViewSet(BaseReviewViewSet):
    """
    ViewSet for Hostel reviews.
    """
    serializer_class = ReviewSerializer
    filterset_fields = ["hostel", "booking"]

    def perform_create(self, serializer):
        booking = serializer.validated_data.get("booking")
        if booking and not serializer.validated_data.get("hostel"):
            serializer.validated_data["hostel"] = booking.hostel
        super().perform_create(serializer)

    def get_queryset(self):
        queryset = Review.objects.select_related("hostel", "user", "booking")
        hostel_id = self.request.query_params.get("hostel") or self.request.query_params.get("hostel_id")
        if hostel_id:
            queryset = queryset.filter(hostel_id=hostel_id)
        if not self.request.user.is_staff:
            return queryset.filter(is_approved=True).order_by("-created_at")
        return queryset.all().order_by("-created_at")


class HotelReviewViewSet(BaseReviewViewSet):
    """
    ViewSet for Hotel reviews.
    Allows filtering by hotel ID, hotel slug, or booking.
    """
    serializer_class = HotelReviewSerializer
    filterset_fields = ["hotel", "booking"]

    def perform_create(self, serializer):
        booking = serializer.validated_data.get("booking")
        if booking and not serializer.validated_data.get("hotel"):
            serializer.validated_data["hotel"] = booking.hotel
        super().perform_create(serializer)

    def get_queryset(self):
        queryset = HotelReview.objects.select_related("hotel", "user", "booking")
        hotel_id = self.request.query_params.get("hotel") or self.request.query_params.get("hotel_id")
        if hotel_id:
            queryset = queryset.filter(hotel_id=hotel_id)
        hotel_slug = self.request.query_params.get("hotel_slug")
        if hotel_slug:
            queryset = queryset.filter(hotel__slug=hotel_slug)
        if not self.request.user.is_staff:
            return queryset.filter(is_approved=True).order_by("-created_at")
        return queryset.all().order_by("-created_at")


class VacationRentalReviewViewSet(BaseReviewViewSet):
    """
    ViewSet for Vacation Rental reviews.
    Allows filtering by rental ID, rental slug, or booking.
    """
    serializer_class = VacationRentalReviewSerializer
    filterset_fields = ["rental", "booking"]

    def perform_create(self, serializer):
        booking = serializer.validated_data.get("booking")
        if booking and not serializer.validated_data.get("rental"):
            serializer.validated_data["rental"] = booking.rental
        super().perform_create(serializer)

    def get_queryset(self):
        queryset = VacationRentalReview.objects.select_related("rental", "user", "booking")
        rental_id = self.request.query_params.get("rental") or self.request.query_params.get("rental_id")
        if rental_id:
            queryset = queryset.filter(rental_id=rental_id)
        rental_slug = self.request.query_params.get("rental_slug")
        if rental_slug:
            queryset = queryset.filter(rental__slug=rental_slug)
        if not self.request.user.is_staff:
            return queryset.filter(is_approved=True).order_by("-created_at")
        return queryset.all().order_by("-created_at")
