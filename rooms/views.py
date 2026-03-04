from rest_framework import viewsets, permissions
from .models import RoomType, Bed
from .serializers import RoomTypeSerializer, BedSerializer


class RoomTypeViewSet(viewsets.ModelViewSet):
    queryset = RoomType.objects.select_related("hostel").all()
    serializer_class = RoomTypeSerializer
    permission_classes = [permissions.AllowAny]


class BedViewSet(viewsets.ModelViewSet):
    queryset = Bed.objects.select_related("room_type").all()
    serializer_class = BedSerializer
    permission_classes = [permissions.AllowAny]
