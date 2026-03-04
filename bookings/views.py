from rest_framework import viewsets, permissions
from .models import Booking
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related("user", "hostel", "room_type").all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
