import logging
import uuid

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Payment, Subscription
from .serializers import PaymentSerializer, SubscriptionSerializer
from .services.payment_service import PaymentService, PaymentError

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PAYMENT VIEWSET — thin views, business logic in PaymentService
# ═══════════════════════════════════════════════════════════════════════════

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("booking").all()
    serializer_class = PaymentSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ["create_razorpay_order", "verify_razorpay_payment"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

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

    # ─── Create Razorpay Order (Public — guest checkout) ─────────────────
    @action(detail=False, methods=["post"])
    def create_razorpay_order(self, request):
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response(
                {"detail": "booking_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = PaymentService.create_order(booking_id)
            return Response(result, status=status.HTTP_200_OK)
        except PaymentError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ─── Verify Razorpay Payment (Public — frontend callback) ───────────
    @action(detail=False, methods=["post"])
    def verify_razorpay_payment(self, request):
        order_id = request.data.get("order_id")
        payment_id = request.data.get("payment_id")
        signature = request.data.get("signature")

        try:
            result = PaymentService.verify_payment(order_id, payment_id, signature)
            return Response(result, status=status.HTTP_200_OK)
        except PaymentError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ═══════════════════════════════════════════════════════════════════════════
# RAZORPAY WEBHOOK — csrf_exempt, standalone view
# ═══════════════════════════════════════════════════════════════════════════

@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def razorpay_webhook(request):
    """
    POST /api/payments/webhook/

    Razorpay calls this server-to-server.
    This is the PRIMARY source of truth for payment confirmation.
    The frontend verify endpoint is a secondary fallback.
    """
    signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")

    if not signature:
        return Response(
            {"detail": "Missing webhook signature."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = PaymentService.handle_webhook(request.body, signature)
        return Response(result, status=status.HTTP_200_OK)
    except PaymentError as e:
        logger.warning("Webhook rejected: %s", e)
        return Response(
            {"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ═══════════════════════════════════════════════════════════════════════════
# SUBSCRIPTION VIEWSET — untouched
# ═══════════════════════════════════════════════════════════════════════════

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
