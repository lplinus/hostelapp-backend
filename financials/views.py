from decimal import Decimal
from django.db.models import Sum
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from hotels.models import HotelBooking
from vacanationrentals.models import VacationRentalBooking
from .models import (
    FinancialTransaction,
    PayoutBatch,
    GstInvoice,
    PropertyExpense,
    StreamChoices,
)
from .serializers import (
    FinancialTransactionSerializer,
    PayoutBatchSerializer,
    GstInvoiceSerializer,
    PropertyExpenseSerializer,
)


class _OwnerScopedFinancialViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = self.queryset.filter(owner=self.request.user)
        stream = self.request.query_params.get("stream")
        if stream in (StreamChoices.HOTEL, StreamChoices.VACATION_RENTAL):
            qs = qs.filter(stream=stream)
        return qs

    def perform_create(self, serializer):
        hotel = serializer.validated_data.get("hotel")
        vacation = serializer.validated_data.get("vacation_rental")
        if hotel and hotel.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You do not own this hotel.")
        if vacation and vacation.host != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You do not host this vacation rental.")
        serializer.save(owner=self.request.user)


class FinancialTransactionViewSet(_OwnerScopedFinancialViewSet):
    queryset = FinancialTransaction.objects.all()
    serializer_class = FinancialTransactionSerializer


class PayoutBatchViewSet(_OwnerScopedFinancialViewSet):
    queryset = PayoutBatch.objects.all()
    serializer_class = PayoutBatchSerializer


class GstInvoiceViewSet(_OwnerScopedFinancialViewSet):
    queryset = GstInvoice.objects.all()
    serializer_class = GstInvoiceSerializer


class PropertyExpenseViewSet(_OwnerScopedFinancialViewSet):
    queryset = PropertyExpense.objects.all()
    serializer_class = PropertyExpenseSerializer


class FinancialsOverviewView(APIView):
    """
    Aggregates owner financial KPIs (gross revenue from live bookings + payouts,
    pending settlements, GST collected, and logged expenses) per stream.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        stream = request.query_params.get("stream", StreamChoices.HOTEL)
        if stream not in (StreamChoices.HOTEL, StreamChoices.VACATION_RENTAL):
            stream = StreamChoices.HOTEL

        if stream == StreamChoices.HOTEL:
            booking_qs = HotelBooking.objects.filter(
                hotel__owner=user,
                status__in=["confirmed", "checked_in", "completed"],
            ).select_related("hotel", "guest_details")
            booking_revenue = booking_qs.aggregate(total=Sum("total_amount")).get("total") or Decimal("0.00")
        else:
            booking_qs = VacationRentalBooking.objects.filter(
                rental__host=user,
                status__in=["confirmed", "checked_in", "completed"],
            ).select_related("rental", "guest_details")
            booking_revenue = booking_qs.aggregate(total=Sum("total_price")).get("total") or Decimal("0.00")

        payouts_qs = PayoutBatch.objects.filter(owner=user, stream=stream)
        invoices_qs = GstInvoice.objects.filter(owner=user, stream=stream)
        expenses_qs = PropertyExpense.objects.filter(owner=user, stream=stream)
        tx_qs = FinancialTransaction.objects.filter(owner=user, stream=stream)

        paid_payouts = payouts_qs.filter(status=PayoutBatch.Status.PAID).aggregate(
            total=Sum("net_payout")
        ).get("total") or Decimal("0.00")
        pending_payouts = payouts_qs.exclude(status=PayoutBatch.Status.PAID).aggregate(
            total=Sum("net_payout")
        ).get("total") or Decimal("0.00")
        gst_total = invoices_qs.aggregate(total=Sum("gst_amount")).get("total") or Decimal("0.00")
        expense_total = expenses_qs.aggregate(total=Sum("amount")).get("total") or Decimal("0.00")

        # Fall back to derived GST / pending settlement from live bookings when no manual batches exist
        if gst_total == Decimal("0.00") and booking_revenue > Decimal("0.00"):
            gst_total = (Decimal(str(booking_revenue)) * Decimal("0.12") / Decimal("1.12")).quantize(Decimal("0.01"))
        if pending_payouts == Decimal("0.00") and paid_payouts == Decimal("0.00") and booking_revenue > Decimal("0.00"):
            pending_payouts = (Decimal(str(booking_revenue)) * Decimal("0.90")).quantize(Decimal("0.01"))

        transactions_data = FinancialTransactionSerializer(tx_qs[:25], many=True).data
        if not transactions_data:
            derived_txs = []
            for b in booking_qs.order_by("-created_at")[:25]:
                prop_name = b.hotel.name if stream == StreamChoices.HOTEL else b.rental.title
                amt = b.total_amount if stream == StreamChoices.HOTEL else b.total_price
                derived_txs.append({
                    "id": str(b.id),
                    "stream": stream,
                    "reference": b.booking_reference,
                    "property_name": prop_name,
                    "transaction_type": "booking_credit",
                    "transaction_type_display": "Booking Credit",
                    "amount": str(amt or "0.00"),
                    "status": "settled",
                    "status_display": "Settled",
                    "transaction_date": b.created_at.date().isoformat(),
                })
            transactions_data = derived_txs

        invoices_data = GstInvoiceSerializer(invoices_qs[:25], many=True).data
        if not invoices_data:
            derived_invs = []
            for b in booking_qs.order_by("-created_at")[:25]:
                prop_name = b.hotel.name if stream == StreamChoices.HOTEL else b.rental.title
                guest_name = b.guest_details.guest_name if getattr(b, "guest_details", None) else "Guest"
                total_amt = Decimal(str((b.total_amount if stream == StreamChoices.HOTEL else b.total_price) or 0))
                taxable = (total_amt / Decimal("1.12")).quantize(Decimal("0.01"))
                gst = (total_amt - taxable).quantize(Decimal("0.01"))
                derived_invs.append({
                    "id": str(b.id),
                    "stream": stream,
                    "invoice_no": f"INV-{b.booking_reference}",
                    "guest_name": guest_name,
                    "property_name": prop_name,
                    "taxable_amount": str(taxable),
                    "gst_amount": str(gst),
                    "total_amount": str(total_amt),
                    "status": "issued",
                    "status_display": "Issued",
                    "invoice_date": b.created_at.date().isoformat(),
                })
            invoices_data = derived_invs

        return Response({
            "stream": stream,
            "gross_revenue": float(booking_revenue),
            "net_payouts": float(paid_payouts),
            "pending_settlement": float(pending_payouts),
            "gst_collected": float(gst_total),
            "total_expenses": float(expense_total),
            "transactions": transactions_data,
            "payouts": PayoutBatchSerializer(payouts_qs[:25], many=True).data,
            "invoices": invoices_data,
            "expenses": PropertyExpenseSerializer(expenses_qs[:50], many=True).data,
        })
