"""
Payment service — ALL payment business logic lives here.

Views are thin wrappers; they only handle request/response.
"""

import hashlib
import hmac
import logging

import razorpay
from django.conf import settings
from django.db import transaction

from bookings.models import Booking
from payments.models import Payment

logger = logging.getLogger(__name__)

# ── Razorpay client (singleton) ─────────────────────────────────────────
_razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


class PaymentError(Exception):
    """Raised when a payment operation fails."""
    pass


class PaymentService:
    """Production-grade Razorpay payment service."""

    # ─── 1. CREATE ORDER ─────────────────────────────────────────────────
    @staticmethod
    def create_order(booking_id: str) -> dict:
        """
        Create a Razorpay order from a pending booking.

        Returns dict: {"order_id", "amount", "currency"}
        Raises PaymentError on any failure.
        """
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            raise PaymentError("Booking not found.")

        if booking.status != "pending":
            raise PaymentError(
                f"Booking is already '{booking.status}'. Only pending bookings can be paid."
            )

        # ── FIXED Booking Fee of ₹59 as per user requirement ──
        # The remainder will be collected at the property.
        if booking.payment_method == "online":
            amount_paise = 5900  # ₹59.00
        else:
            amount_paise = int(booking.total_price * 100)

        try:
            order = _razorpay_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {"booking_id": str(booking.id)},
            })
        except Exception as e:
            logger.error("Razorpay order creation failed: %s", e)
            raise PaymentError("Failed to create payment order. Please try again.")

        # ── Persist payment record ───────────────────────────────────────
        Payment.objects.update_or_create(
            booking=booking,
            defaults={
                "provider": "razorpay",
                "amount": booking.total_price,
                "status": "pending",
                "razorpay_order_id": order["id"],
            },
        )

        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
        }

    # ─── 2. VERIFY PAYMENT (frontend callback) ──────────────────────────
    @staticmethod
    def verify_payment(order_id: str, payment_id: str, signature: str) -> dict:
        """
        Verify Razorpay signature + server-side amount, then confirm booking.

        Returns dict: {"detail": "..."}
        Raises PaymentError on failure.
        """
        if not order_id or not payment_id or not signature:
            raise PaymentError("Missing required payment fields.")

        try:
            payment = Payment.objects.select_related("booking").get(
                razorpay_order_id=order_id
            )
        except Payment.DoesNotExist:
            raise PaymentError("Payment record not found for this order.")

        # ── Idempotency: already captured → return success ───────────────
        if payment.status == "captured":
            return {"detail": "Payment already verified and booking confirmed."}

        # ── 1. Verify Razorpay signature ─────────────────────────────────
        try:
            _razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
        except razorpay.errors.SignatureVerificationError:
            raise PaymentError("Payment signature verification failed.")

        # ── 2. Server-side amount verification ───────────────────────────
        try:
            rz_order = _razorpay_client.order.fetch(order_id)
        except Exception as e:
            logger.error("Razorpay order fetch failed: %s", e)
            raise PaymentError("Could not verify payment amount.")

        if payment.booking.payment_method == "online":
            expected_amount = 5900 # ₹59
        else:
            expected_amount = int(payment.booking.total_price * 100)
        
        if rz_order["amount"] != expected_amount:
            logger.warning(
                "Amount mismatch: Razorpay=%s, Expected=%s, order=%s",
                rz_order["amount"], expected_amount, order_id,
            )
            raise PaymentError("Payment amount does not match booking amount.")

        # ── 3. Atomically update payment + booking ───────────────────────
        PaymentService._confirm_payment(payment, payment_id, signature)

        return {"detail": "Payment verified and booking confirmed."}

    # ─── 3. WEBHOOK HANDLER ──────────────────────────────────────────────
    @staticmethod
    def handle_webhook(payload: bytes, signature: str) -> dict:
        """
        Handle Razorpay webhook event.

        Returns dict: {"detail": "..."}
        Raises PaymentError on failure.
        """
        # ── Verify webhook signature ─────────────────────────────────────
        expected_sig = hmac.new(
            key=settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            raise PaymentError("Invalid webhook signature.")

        import json
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            raise PaymentError("Invalid webhook payload.")

        event = data.get("event", "")

        # ── Only handle payment.captured ─────────────────────────────────
        if event != "payment.captured":
            return {"detail": f"Event '{event}' ignored."}

        entity = data.get("payload", {}).get("payment", {}).get("entity", {})
        rz_order_id = entity.get("order_id")
        rz_payment_id = entity.get("id")

        if not rz_order_id:
            raise PaymentError("Missing order_id in webhook payload.")

        try:
            payment = Payment.objects.select_related("booking").get(
                razorpay_order_id=rz_order_id
            )
        except Payment.DoesNotExist:
            logger.warning("Webhook: No payment found for order %s", rz_order_id)
            raise PaymentError("Payment record not found.")

        # ── Idempotency ──────────────────────────────────────────────────
        if payment.status == "captured":
            return {"detail": "Payment already captured."}

        # ── Amount verification ──────────────────────────────────────────
        if payment.booking.payment_method == "online":
            expected_amount = 5900 # ₹59
        else:
            expected_amount = int(payment.booking.total_price * 100)
            
        webhook_amount = entity.get("amount", 0)

        if webhook_amount != expected_amount:
            logger.warning(
                "Webhook amount mismatch: got=%s, expected=%s, order=%s",
                webhook_amount, expected_amount, rz_order_id,
            )
            raise PaymentError("Payment amount mismatch.")

        # ── Confirm ──────────────────────────────────────────────────────
        PaymentService._confirm_payment(payment, rz_payment_id, "")

        logger.info("Webhook: Payment %s confirmed for booking %s", rz_order_id, payment.booking_id)
        return {"detail": "Webhook processed. Payment confirmed."}

    @staticmethod
    @transaction.atomic
    def _confirm_payment(payment: Payment, payment_id: str, signature: str):
        """Atomically mark payment as captured and booking as confirmed."""
        from bookings.services.booking_email_service import BookingEmailService
        
        payment.status = "captured"
        payment.razorpay_payment_id = payment_id
        payment.razorpay_signature = signature
        payment.save(update_fields=[
            "status", "razorpay_payment_id", "razorpay_signature", "updated_at"
        ])

        booking = payment.booking
        booking.status = "confirmed"
        booking.save(update_fields=["status"])
        
        # Trigger confirmation email ONLY after successful payment confirmation
        BookingEmailService.send_booking_confirmation(booking, payment_id=payment_id)
