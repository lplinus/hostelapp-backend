from django.conf import settings
from django.db import models
from django.utils import timezone
from Hbackend.base_models import SoftDeleteModel


class StreamChoices(models.TextChoices):
    HOTEL = "hotel", "Hotel"
    VACATION_RENTAL = "vacation_rental", "Vacation Rental"


class FinancialTransaction(SoftDeleteModel):
    class TransactionType(models.TextChoices):
        BOOKING_CREDIT = "booking_credit", "Booking Credit"
        PAYOUT = "payout", "Payout"
        REFUND = "refund", "Refund"
        TAX_DEDUCTION = "tax_deduction", "Tax Deduction"

    class Status(models.TextChoices):
        SETTLED = "settled", "Settled"
        PROCESSING = "processing", "Processing"
        PENDING = "pending", "Pending"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="financial_transactions",
    )
    stream = models.CharField(
        max_length=20,
        choices=StreamChoices.choices,
        default=StreamChoices.HOTEL,
    )
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="financial_transactions",
    )
    vacation_rental = models.ForeignKey(
        "vacanationrentals.VacationRental",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="financial_transactions",
    )
    reference = models.CharField(max_length=60)
    property_name = models.CharField(max_length=160)
    transaction_type = models.CharField(
        max_length=25,
        choices=TransactionType.choices,
        default=TransactionType.BOOKING_CREDIT,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SETTLED,
    )
    transaction_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at"]
        verbose_name = "Financial Transaction"
        verbose_name_plural = "Financial Transactions"

    def __str__(self):
        return f"{self.reference} ({self.property_name} - ₹{self.amount})"


class PayoutBatch(SoftDeleteModel):
    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        SCHEDULED = "scheduled", "Scheduled"
        PROCESSING = "processing", "Processing"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payout_batches",
    )
    stream = models.CharField(
        max_length=20,
        choices=StreamChoices.choices,
        default=StreamChoices.HOTEL,
    )
    batch_id = models.CharField(max_length=60)
    property_summary = models.CharField(max_length=200)
    period = models.CharField(max_length=100)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    bank_account = models.CharField(max_length=100, default="HDFC •••• 4821")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
    )
    payout_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-payout_date", "-created_at"]
        verbose_name = "Payout Batch"
        verbose_name_plural = "Payout Batches"

    def __str__(self):
        return f"{self.batch_id} (₹{self.net_payout})"


class GstInvoice(SoftDeleteModel):
    class Status(models.TextChoices):
        FILED = "filed", "Filed"
        ISSUED = "issued", "Issued"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gst_invoices",
    )
    stream = models.CharField(
        max_length=20,
        choices=StreamChoices.choices,
        default=StreamChoices.HOTEL,
    )
    invoice_no = models.CharField(max_length=60)
    guest_name = models.CharField(max_length=120)
    property_name = models.CharField(max_length=160)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ISSUED,
    )
    invoice_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-invoice_date", "-created_at"]
        verbose_name = "GST Invoice"
        verbose_name_plural = "GST Invoices"

    def __str__(self):
        return f"{self.invoice_no} ({self.guest_name})"


class PropertyExpense(SoftDeleteModel):
    class Category(models.TextChoices):
        HOUSEKEEPING = "housekeeping", "Housekeeping"
        MAINTENANCE = "maintenance", "Maintenance"
        UTILITIES = "utilities", "Utilities"
        STAFF = "staff", "Staff"

    class PaymentMode(models.TextChoices):
        UPI = "upi", "UPI"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CARD = "card", "Card"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_expenses",
    )
    stream = models.CharField(
        max_length=20,
        choices=StreamChoices.choices,
        default=StreamChoices.HOTEL,
    )
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="property_expenses",
    )
    vacation_rental = models.ForeignKey(
        "vacanationrentals.VacationRental",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="property_expenses",
    )
    property_name = models.CharField(max_length=160)
    category = models.CharField(
        max_length=25,
        choices=Category.choices,
        default=Category.HOUSEKEEPING,
    )
    description = models.TextField(blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_mode = models.CharField(
        max_length=25,
        choices=PaymentMode.choices,
        default=PaymentMode.UPI,
    )
    expense_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        verbose_name = "Property Expense"
        verbose_name_plural = "Property Expenses"

    def __str__(self):
        return f"{self.property_name} - {self.get_category_display()} (₹{self.amount})"
