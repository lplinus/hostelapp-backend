import logging
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="payments.tasks.process_payment_webhook_task",
)
def process_payment_webhook_task(self, payload_str, signature):
    """
    Celery background task to handle Razorpay webhooks asynchronously.
    
    Ensures that when many users complete payments concurrently:
    1. The webhook HTTP endpoint returns 200 OK immediately without blocking.
    2. Background worker verifies signature, amount, updates payment status atomically,
       and triggers confirmation notifications via Celery.
    """
    from payments.services.payment_service import PaymentService, PaymentError

    try:
        payload_bytes = payload_str.encode("utf-8")
        result = PaymentService.handle_webhook(payload_bytes, signature)
        logger.info(f"[Celery] Webhook processed successfully: {result}")
        return result
    except PaymentError as pe:
        logger.warning(f"[Celery] Webhook business error: {pe}")
        return {"error": str(pe)}
    except Exception as exc:
        logger.error(f"[Celery] Webhook processing exception: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name="payments.tasks.process_payment_confirmation_task",
)
def process_payment_confirmation_task(self, payment_id, rz_payment_id="", signature=""):
    """
    Celery task to confirm a payment atomically and trigger booking confirmation.
    Row-level lock (select_for_update) guarantees idempotency under concurrent load.
    """
    from payments.models import Payment
    from bookings.tasks import process_booking_confirmation_task

    try:
        with transaction.atomic():
            payment = (
                Payment.objects.select_for_update()
                .select_related("booking")
                .get(id=payment_id)
            )

            if payment.status == "captured":
                logger.info(f"[Celery] Payment {payment_id} already captured. Skipping.")
                return f"Payment {payment_id} already captured"

            payment.status = "captured"
            if rz_payment_id:
                payment.razorpay_payment_id = rz_payment_id
            if signature:
                payment.razorpay_signature = signature
            payment.save(
                update_fields=["status", "razorpay_payment_id", "razorpay_signature", "updated_at"]
            )

            booking = payment.booking
            booking.status = "confirmed"
            booking.save(update_fields=["status"])

            # Queue booking confirmation email and QR generation
            transaction.on_commit(
                lambda: process_booking_confirmation_task.delay(
                    str(booking.id), payment_id=rz_payment_id
                )
            )

        logger.info(f"[Celery] Payment {payment_id} captured and booking confirmed.")
        return f"Payment {payment_id} captured"

    except Payment.DoesNotExist:
        logger.error(f"[Celery] Payment {payment_id} not found.")
        return f"Payment {payment_id} not found"
    except Exception as exc:
        logger.error(f"[Celery] Error confirming payment {payment_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="payments.tasks.reconcile_pending_payments_task",
)
def reconcile_pending_payments_task(lookback_minutes=60):
    """
    Periodic Celery task to auto-reconcile pending payments with Razorpay.
    
    When multiple users initiate payments, network drops or tab closures can leave
    payments in 'pending' status even if the user was charged.
    This task queries Razorpay for pending orders created within the lookback window
    and automatically confirms any payments that Razorpay marked as captured.
    """
    import razorpay
    from payments.models import Payment

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    cutoff_time = timezone.now() - timedelta(minutes=lookback_minutes)
    pending_payments = Payment.objects.filter(
        status="pending",
        provider="razorpay",
        created_at__gte=cutoff_time,
    ).exclude(razorpay_order_id__isnull=True).exclude(razorpay_order_id="")

    count = pending_payments.count()
    if count == 0:
        logger.info("[Celery Reconcile] No pending payments to reconcile.")
        return "No pending payments"

    logger.info(f"[Celery Reconcile] Checking {count} pending payments with Razorpay...")
    reconciled_count = 0

    for payment in pending_payments:
        order_id = payment.razorpay_order_id
        try:
            order_data = client.order.fetch(order_id)
            order_status = order_data.get("status")

            if order_status == "paid":
                # Find the captured payment id
                payments_resp = client.order.payments(order_id)
                items = payments_resp.get("items", [])
                captured_payment = next(
                    (p for p in items if p.get("status") == "captured"), None
                )

                rz_pay_id = captured_payment.get("id") if captured_payment else ""
                process_payment_confirmation_task.delay(payment.id, rz_payment_id=rz_pay_id)
                reconciled_count += 1
                logger.info(
                    f"[Celery Reconcile] Order {order_id} was paid on Razorpay. Dispatched confirmation."
                )

        except Exception as e:
            logger.warning(
                f"[Celery Reconcile] Could not fetch Razorpay order {order_id}: {e}"
            )

    return f"Reconciled {reconciled_count} of {count} pending payments"
