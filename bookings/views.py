from rest_framework import viewsets, permissions, decorators
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related("user", "hostel", "room_type").order_by(
        "-created_at"
    )
    serializer_class = BookingSerializer
    # def perform_create(self, serializer):
    #     serializer.save(user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()

        from django.db.models import Q

        return super().get_queryset().filter(Q(user=user) | Q(hostel__owner=user))

    @decorators.action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def owner(self, request):
        bookings = Booking.objects.filter(hostel__owner=request.user).order_by(
            "-created_at"
        )
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
