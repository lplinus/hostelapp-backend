from rest_framework import serializers
from .models import Order, OrderItem
from marketplace.models import Product
from vendors.models import Vendor
from hostels.models import Hostel

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_name_at_order', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_name_at_order', 
            'quantity', 'unit_price', 'total_price'
        ]
        read_only_fields = ['id', 'product_name', 'product_name_at_order', 'total_price']

class OrderItemCreateSerializer(serializers.Serializer):
    """
    Used for structured order line items.
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    hostel_name = serializers.CharField(source='hostel.name', read_only=True)
    hostel_address = serializers.CharField(source='hostel.address', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'hostel', 'hostel_name', 'hostel_address', 'vendor', 'vendor_name', 
            'status', 'order_type', 'scan_image', 'note', 
            'total_amount', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'hostel_name', 'hostel_address', 'vendor_name', 'total_amount', 'created_at', 'updated_at']

class StructuredOrderCreateSerializer(serializers.Serializer):
    hostel_id = serializers.IntegerField()
    vendor_id = serializers.IntegerField()
    items = OrderItemCreateSerializer(many=True)
    note = serializers.CharField(required=False, allow_blank=True)

class WholesaleOrderItemSerializer(serializers.Serializer):
    """
    Serializer for individual items in a wholesale order.
    Supports both catalog products and manual entries.
    """
    product_id = serializers.IntegerField(required=False, allow_null=True)
    manual_name = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, data):
        if not data.get('product_id') and not data.get('manual_name'):
            raise serializers.ValidationError("Either product_id or manual_name must be provided.")
        return data

class WholesaleOrderCreateSerializer(serializers.Serializer):
    hostel_id = serializers.IntegerField()
    vendor_id = serializers.IntegerField()
    items = WholesaleOrderItemSerializer(many=True)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Wholesale orders must contain at least 5 distinct items.")
        return value

class ImageScanOrderCreateSerializer(serializers.Serializer):
    hostel_id = serializers.IntegerField()
    vendor_id = serializers.IntegerField()
    scan_image = serializers.ImageField()
    note = serializers.CharField(required=False, allow_blank=True)
