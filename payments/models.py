from django.conf import settings
from django.db import models
from Hbackend.base_models import SoftDeleteModel
from bookings.models import Booking
from publicpages.models import PricingPlan


class Payment(SoftDeleteModel):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("captured", "Captured"),
        ("failed", "Failed"),
    )

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="payment"
    )

    provider = models.CharField(max_length=50, default="razorpay")
    transaction_id = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    razorpay_order_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True
    )
    razorpay_payment_id = models.CharField(max_length=255, blank=True, default="")
    razorpay_signature = models.CharField(max_length=255, blank=True, default="")

    paid_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider} - {self.razorpay_order_id or self.transaction_id}"


#subscription model
class Subscription(SoftDeleteModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Dummy order details
    transaction_id = models.CharField(max_length=255, unique=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


class VendorPricingPlan(SoftDeleteModel):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency_symbol = models.CharField(max_length=10, default="₹")
    period = models.CharField(max_length=50, blank=True)  # e.g., /month or /year
    is_popular = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    gradient = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. from-blue-600 to-indigo-600")

    class Meta:
        db_table = "payments_vendor_pricing_plans"
        ordering = ["order"]

    def __str__(self):
        return self.name

class VendorPricingFeature(models.Model):
    plan = models.ForeignKey(VendorPricingPlan, on_delete=models.CASCADE, related_name="features")
    feature_text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "payments_vendor_pricing_features"
        ordering = ["order"]

    def __str__(self):
        return self.feature_text

class VendorSubscription(SoftDeleteModel):
    """
    Dedicated subscription model for Marketplace Vendors.
    Separated from the core owner Subscription to allow for unique vendor 
    constraints (like max products, varying commission rates) at scale.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendor_subscriptions"
    )
    plan = models.ForeignKey(VendorPricingPlan, on_delete=models.CASCADE)
    
    # Generic status fields
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Vendor-specific scalability fields
    max_products_allowed = models.PositiveIntegerField(
        default=50, 
        help_text="Maximum number of active products the vendor can list."
    )
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=5.00,
        help_text="Commission fee percentage applied to vendor sales (e.g., 5.00 for 5%)."
    )
    can_feature_products = models.BooleanField(
        default=False,
        help_text="Whether this vendor is allowed to feature product listings."
    )
    has_dedicated_support = models.BooleanField(
        default=False,
        help_text="Whether this vendor has priority 24/7 dedicated support."
    )

    # Payment details
    transaction_id = models.CharField(max_length=255, unique=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_vendor_subscriptions"
        verbose_name = "Vendor Subscription"
        verbose_name_plural = "Vendor Subscriptions"

    def __str__(self):
        return f"Vendor: {self.user.username} - Plan: {self.plan.name}"
