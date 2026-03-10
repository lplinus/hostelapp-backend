from rest_framework import viewsets, permissions, decorators
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .models import RoomType, Bed
from .serializers import RoomTypeSerializer, BedSerializer


from .services import GroupedRoomsService


class IsRoomOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.hostel.owner == request.user


class RoomTypeViewSet(viewsets.ModelViewSet):
    queryset = RoomType.objects.select_related("hostel").all()
    serializer_class = RoomTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsRoomOwner]
    pagination_class = None

    def perform_create(self, serializer):
        hostel = serializer.validated_data.get("hostel")
        if hostel and getattr(hostel, "owner", None) != self.request.user:
            raise PermissionDenied("You do not own this hostel.")
        serializer.save()

    @decorators.action(
        detail=False,
        methods=["get"],
        url_path="my-rooms",
        permission_classes=[permissions.IsAuthenticated],
    )
    def my_rooms(self, request):
        rooms = RoomType.objects.filter(hostel__owner=request.user)
        serializer = self.get_serializer(rooms, many=True)
        return Response(serializer.data)

    @decorators.action(
        detail=False,
        methods=["get"],
        url_path="grouped-my-rooms",
        permission_classes=[permissions.IsAuthenticated],
    )
    def grouped_my_rooms(self, request):
        data = GroupedRoomsService.get_grouped_rooms(user=request.user)
        return Response(data)


class IsBedOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.room_type.hostel.owner == request.user


class BedViewSet(viewsets.ModelViewSet):
    queryset = Bed.objects.select_related("room_type").all()
    serializer_class = BedSerializer
    permission_classes = [permissions.IsAuthenticated, IsBedOwner]
    pagination_class = None
