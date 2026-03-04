from rest_framework import viewsets, permissions
from .models import Hostel, HostelImage, HostelTypeImage
from .serializers import (
    HostelSerializer,
    HostelImageSerializer,
    HostelTypeImageSerializer,
    CityHostelListSerializer,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class HostelViewSet(viewsets.ModelViewSet):
    queryset = (
        Hostel.objects.select_related("city", "area", "owner")
        .prefetch_related("amenities", "images", "room_types")
        .all()
    )
    serializer_class = HostelSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"


class HostelImageViewSet(viewsets.ModelViewSet):
    queryset = HostelImage.objects.select_related("hostel").all()
    serializer_class = HostelImageSerializer
    permission_classes = [permissions.AllowAny]


class HostelTypeImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HostelTypeImage.objects.all()
    serializer_class = HostelTypeImageSerializer
    permission_classes = [permissions.AllowAny]


class TypeHostelsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, type_slug, *args, **kwargs):
        if type_slug == "all":
            # Return all active hostels
            hostels = (
                Hostel.objects.filter(is_active=True)
                .select_related("city", "area")
                .prefetch_related("images")
            )
            type_name = "All Hostels"
        else:
            # type_slug corresponds to hostel_type e.g., "boys", "girls"
            hostels = (
                Hostel.objects.filter(hostel_type=type_slug, is_active=True)
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
