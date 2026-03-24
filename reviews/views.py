"""
Views for the Reviews application.
Allows users to post reviews for hostels. 
Includes logic for moderation (auto-approval settings) and ownership verification.
"""
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Review
from .serializers import ReviewSerializer


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


from django.conf import settings
from django.utils import timezone
from datetime import timedelta


from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Review model.
    Handles submission of new reviews, including auto-population of names 
    and handling of approval delays based on project settings.
    """
    serializer_class = ReviewSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsReviewOwnerOrReadOnly]
    pagination_class = None
    filterset_fields = ["hostel"]

    def get_queryset(self):
        queryset = Review.objects.select_related("hostel", "user")
        if not self.request.user.is_staff:
            return queryset.filter(is_approved=True).order_by("-created_at")
        return queryset.all().order_by("-created_at")

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [p() for p in self.permission_classes]

    def perform_create(self, serializer):
        is_approved = getattr(settings, "REVIEWS_AUTO_APPROVE", False)
        publish_delay = getattr(settings, "REVIEWS_PUBLISH_DELAY", 0)
        published_at = timezone.now() + timedelta(seconds=publish_delay)
        
        user = self.request.user if self.request.user.is_authenticated else None
        
        # Auto-populate name if empty and user is logged in
        name = serializer.validated_data.get('name')
        if not name and user:
            name = f"{user.first_name} {user.last_name}".strip() or user.username

        serializer.save(
            user=user,
            name=name,
            is_approved=is_approved,
            published_at=published_at
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
