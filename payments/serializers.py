from rest_framework import serializers
from .models import Payment, Subscription, VendorPricingPlan, VendorPricingFeature, VendorSubscription


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

class VendorPricingFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorPricingFeature
        fields = ['id', 'feature_text', 'order']

class VendorPricingPlanSerializer(serializers.ModelSerializer):
    features = VendorPricingFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = VendorPricingPlan
        fields = [
            'id', 'name', 'description', 'price', 'currency_symbol', 
            'period', 'is_popular', 'gradient', 'order', 'features'
        ]

class VendorSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.ReadOnlyField(source="plan.name")

    class Meta:
        model = VendorSubscription
        fields = [
            "id",
            "user",
            "plan",
            "plan_name",
            "start_date",
            "end_date",
            "is_active",
            "max_products_allowed",
            "commission_rate",
            "can_feature_products",
            "has_dedicated_support",
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
