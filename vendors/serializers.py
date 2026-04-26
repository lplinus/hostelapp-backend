from rest_framework import serializers
from .models import Vendor
from marketplace.models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "vendor",
            "name",
            "description",
            "price",
            "image",
            "is_active",
        ]
        read_only_fields = ["id", "vendor"]


class VendorSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            "id",
            "owner",
            "business_name",
            "slug",
            "description",
            "logo",
            "address",
            "contact_phone",
            "contact_email",
            "vendor_types",
            "is_active",
            "product_count",
        ]
        read_only_fields = ["id", "owner", "slug", "product_count"]

    def get_product_count(self, obj) -> int:
        return obj.marketplace_products.count()


class VendorDetailSerializer(VendorSerializer):
    products = ProductSerializer(
        many=True, read_only=True, source="marketplace_products"
    )

    class Meta(VendorSerializer.Meta):
        fields = VendorSerializer.Meta.fields + ["products"]
