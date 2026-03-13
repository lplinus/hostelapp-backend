from rest_framework import serializers
from .models import Payment, Subscription


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.ReadOnlyField(source="plan.name")

    class Meta:
        model = Subscription
        fields = [
            "id",
            "user",
            "plan",
            "plan_name",
            "start_date",
            "end_date",
            "is_active",
            "transaction_id",
            "amount_paid",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "start_date",
            "is_active",
            "transaction_id",
            "amount_paid",
            "created_at",
            "updated_at",
        ]
