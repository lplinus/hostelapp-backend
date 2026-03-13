from django.contrib import admin
from .models import Payment, Subscription


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "booking", "amount", "status", "paid_at"]
    search_fields = ["transaction_id", "booking__user__email"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "transaction_id", "amount_paid", "is_active", "start_date"]
    list_filter = ["is_active", "plan"]
    search_fields = ["user__email", "transaction_id"]