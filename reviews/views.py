from rest_framework import viewsets, permissions
from .models import Review
from .serializers import ReviewSerializer


class IsReviewOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("hostel", "user").all()
    serializer_class = ReviewSerializer
    permission_classes = [IsReviewOwnerOrReadOnly]
