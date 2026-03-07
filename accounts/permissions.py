from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "superadmin"


class IsGuest(BasePermission):
    """Allow access only to authenticated users with role 'guest'."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "guest"


class IsHostelOwner(BasePermission):
    """Allow access only to authenticated users with role 'hostel_owner'."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "hostel_owner"
