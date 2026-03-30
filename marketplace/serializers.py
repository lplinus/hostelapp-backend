from rest_framework import serializers
from .models import Category, Product
from vendors.models import Vendor

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'description', 'is_active']
        read_only_fields = ['id', 'slug']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_name', 'vendor', 'vendor_name', 
            'name', 'slug', 'description', 'price', 'image', 
            'stock', 'is_active', 'is_featured'
        ]
        read_only_fields = ['id', 'slug', 'category_name', 'vendor_name']

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Simpler serializer with necessary fields for vendor input.
    """
    category_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Product
        fields = [
            'category_id', 'name', 'description', 'price', 
            'image', 'stock', 'is_active', 'is_featured'
        ]
