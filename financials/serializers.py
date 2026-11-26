from rest_framework import serializers
from .models import (
    FinancialTransaction,
    PayoutBatch,
    GstInvoice,
    PropertyExpense,
)


class FinancialTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    stream_display = serializers.CharField(source="get_stream_display", read_only=True)

    class Meta:
        model = FinancialTransaction
        fields = [
            "id",
            "stream",
            "stream_display",
            "hotel",
            "vacation_rental",
            "reference",
            "property_name",
            "transaction_type",
            "transaction_type_display",
            "amount",
            "status",
            "status_display",
            "transaction_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PayoutBatchSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    stream_display = serializers.CharField(source="get_stream_display", read_only=True)

    class Meta:
        model = PayoutBatch
        fields = [
            "id",
            "stream",
            "stream_display",
            "batch_id",
            "property_summary",
            "period",
            "gross_amount",
            "platform_fee",
            "net_payout",
            "bank_account",
            "status",
            "status_display",
            "payout_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GstInvoiceSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    stream_display = serializers.CharField(source="get_stream_display", read_only=True)

    class Meta:
        model = GstInvoice
        fields = [
            "id",
            "stream",
            "stream_display",
            "invoice_no",
            "guest_name",
            "property_name",
            "taxable_amount",
            "gst_amount",
            "total_amount",
            "status",
            "status_display",
            "invoice_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertyExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    payment_mode_display = serializers.CharField(source="get_payment_mode_display", read_only=True)
    stream_display = serializers.CharField(source="get_stream_display", read_only=True)

    class Meta:
        model = PropertyExpense
        fields = [
            "id",
            "stream",
            "stream_display",
            "hotel",
            "vacation_rental",
            "property_name",
            "category",
            "category_display",
            "description",
            "amount",
            "payment_mode",
            "payment_mode_display",
            "expense_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
