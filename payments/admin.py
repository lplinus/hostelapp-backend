from django.contrib import admin
from .models import Payment, Subscription, VendorSubscription, VendorPricingPlan, VendorPricingFeature


class VendorPricingFeatureInline(admin.TabularInline):
    model = VendorPricingFeature
    extra = 1


@admin.register(VendorPricingPlan)
class VendorPricingPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "period", "is_popular", "order"]
    list_editable = ["price", "is_popular", "order"]
    inlines = [VendorPricingFeatureInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "booking", "amount", "status", "paid_at"]
    search_fields = ["transaction_id", "booking__user__email"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "transaction_id", "amount_paid", "is_active", "start_date"]
    list_filter = ["is_active", "plan"]
    search_fields = ["user__email", "transaction_id"]

@admin.register(VendorSubscription)
class VendorSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "transaction_id", "amount_paid", "is_active", "start_date"]
    list_filter = ["is_active", "plan"]
    search_fields = ["user__email", "transaction_id"]