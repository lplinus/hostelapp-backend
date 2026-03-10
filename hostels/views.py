from rest_framework import viewsets, permissions, decorators, status
from rest_framework.exceptions import PermissionDenied
from .models import Hostel, HostelImage, HostelTypeImage
from .serializers import (
    HostelSerializer,
    HostelWriteSerializer,
    HostelImageSerializer,
    HostelTypeImageSerializer,
    CityHostelListSerializer,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class IsHostelOwner(permissions.BasePermission):
    """Only allow the hostel owner to modify it."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class HostelViewSet(viewsets.ModelViewSet):
    queryset = (
        Hostel.objects.select_related("city", "area", "owner")
        .prefetch_related("amenities", "images", "room_types")
        .all()
    )
    serializer_class = HostelSerializer
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        qs = Hostel.objects.select_related("city", "area", "owner").prefetch_related(
            "amenities", "images", "room_types"
        )
        # For public actions, filter by active and approved
        if self.action in ["list", "retrieve"]:
            return qs.filter(is_active=True, is_approved=True)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return HostelWriteSerializer
        return HostelSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    # ── Owner's hostel list ──────────────────────────────────────────
    @decorators.action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="my-hostels",
    )
    def my_hostels(self, request):
        hostels = (
            Hostel.objects.filter(owner=request.user)
            .select_related("city", "area", "owner")
            .prefetch_related("amenities", "images", "room_types")
        )
        serializer = self.get_serializer(
            hostels, many=True, context={"request": request}
        )
        return Response(serializer.data)

    # ── Owner: get single hostel by ID ───────────────────────────────
    @decorators.action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="my-hostels/(?P<hostel_id>[0-9]+)",
    )
    def my_hostel_detail(self, request, hostel_id=None):
        hostel = get_object_or_404(
            Hostel.objects.select_related("city", "area", "owner").prefetch_related(
                "amenities", "images", "room_types"
            ),
            id=hostel_id,
            owner=request.user,
        )
        serializer = HostelSerializer(hostel, context={"request": request})
        return Response(serializer.data)

    # ── Owner: update hostel by ID ───────────────────────────────────
    @decorators.action(
        detail=False,
        methods=["put", "patch"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="my-hostels/(?P<hostel_id>[0-9]+)/update",
    )
    def my_hostel_update(self, request, hostel_id=None):
        hostel = get_object_or_404(Hostel, id=hostel_id, owner=request.user)
        partial = request.method == "PATCH"
        serializer = HostelWriteSerializer(
            hostel, data=request.data, partial=partial, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Return the full read representation
        read_serializer = HostelSerializer(hostel, context={"request": request})
        return Response(read_serializer.data)

    # ── Owner: delete hostel by ID ───────────────────────────────────
    @decorators.action(
        detail=False,
        methods=["delete"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="my-hostels/(?P<hostel_id>[0-9]+)/delete",
    )
    def my_hostel_delete(self, request, hostel_id=None):
        hostel = get_object_or_404(Hostel, id=hostel_id, owner=request.user)
        hostel.delete()
        return Response(
            {"detail": "Hostel deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


class HostelImageViewSet(viewsets.ModelViewSet):
    queryset = HostelImage.objects.select_related("hostel").all()
    serializer_class = HostelImageSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        hostel = serializer.validated_data.get("hostel")
        if hostel and hostel.owner != self.request.user:
            raise PermissionDenied("You do not own this hostel.")
        serializer.save()

    def perform_update(self, serializer):
        hostel = serializer.instance.hostel
        if hostel.owner != self.request.user:
            raise PermissionDenied("You do not own this hostel.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.hostel.owner != self.request.user:
            raise PermissionDenied("You do not own this hostel.")
        instance.delete()


class HostelTypeImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HostelTypeImage.objects.all()
    serializer_class = HostelTypeImageSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class TypeHostelsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, type_slug, *args, **kwargs):
        if type_slug == "all":
            # Return all active and approved hostels
            hostels = (
                Hostel.objects.filter(is_active=True, is_approved=True)
                .select_related("city", "area")
                .prefetch_related("images")
            )
            type_name = "All Hostels"
        else:
            # type_slug corresponds to hostel_type e.g., "boys", "girls"
            hostels = (
                Hostel.objects.filter(
                    hostel_type=type_slug, is_active=True, is_approved=True
                )
                .select_related("city", "area")
                .prefetch_related("images")
            )
            # Get human-readable name if possible
            choices = dict(Hostel.HostelType.choices)
            type_name = choices.get(type_slug, type_slug)

        serializer = CityHostelListSerializer(
            hostels, many=True, context={"request": request}
        )

        return Response(
            {
                "type": type_name,
                "type_slug": type_slug,
                "total": hostels.count(),
                "results": serializer.data,
            }
        )
