from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("booking").all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(booking__user=user)

    def perform_create(self, serializer):
        booking = serializer.validated_data.get("booking")
        if (
            booking
            and booking.user != self.request.user
            and not self.request.user.is_staff
        ):
            raise PermissionDenied("You do not own this booking.")
        serializer.save()

    def perform_update(self, serializer):
        obj = serializer.instance
        if obj.booking.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You do not own this payment.")
        serializer.save()

    def perform_destroy(self, instance):
        if (
            instance.booking.user != self.request.user
            and not self.request.user.is_staff
        ):
            raise PermissionDenied("You do not own this payment.")
        instance.delete()
