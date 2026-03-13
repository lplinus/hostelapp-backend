import uuid
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .models import Payment, Subscription
from .serializers import PaymentSerializer, SubscriptionSerializer


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


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Subscription.objects.all()
        return Subscription.objects.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        plan = serializer.validated_data.get("plan")

        # Deactivate previous active subscriptions for this user
        Subscription.objects.filter(user=user, is_active=True).update(is_active=False)

        # Create dummy order details
        transaction_id = f"SUB-{uuid.uuid4().hex[:10].upper()}"
        amount_paid = plan.price

        # Set 3 months (90 days) duration
        from django.utils import timezone
        from datetime import timedelta
        start_date = timezone.now()
        end_date = start_date + timedelta(days=90)

        serializer.save(
            user=user,
            transaction_id=transaction_id,
            amount_paid=amount_paid,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )

    @action(detail=False, methods=["get"])
    def current(self, request):
        subscription = Subscription.objects.filter(user=request.user, is_active=True).first()
        if not subscription:
            return Response({"detail": "No active subscription found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)
