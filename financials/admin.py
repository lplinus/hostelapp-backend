from django.contrib import admin
from .models import (
    FinancialTransaction,
    PayoutBatch,
    GstInvoice,
    PropertyExpense,
)


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "owner", "stream", "property_name", "transaction_type", "amount", "status", "transaction_date")
    list_filter = ("stream", "transaction_type", "status")
    search_fields = ("reference", "property_name")


@admin.register(PayoutBatch)
class PayoutBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_id", "owner", "stream", "period", "gross_amount", "net_payout", "status", "payout_date")
    list_filter = ("stream", "status")
    search_fields = ("batch_id", "property_summary")


@admin.register(GstInvoice)
class GstInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "owner", "stream", "guest_name", "property_name", "total_amount", "status", "invoice_date")
    list_filter = ("stream", "status")
    search_fields = ("invoice_no", "guest_name", "property_name")


@admin.register(PropertyExpense)
class PropertyExpenseAdmin(admin.ModelAdmin):
    list_display = ("property_name", "owner", "stream", "category", "amount", "payment_mode", "expense_date")
    list_filter = ("stream", "category", "payment_mode")
    search_fields = ("property_name", "description")
