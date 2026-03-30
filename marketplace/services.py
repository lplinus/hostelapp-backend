from typing import Any, Dict, Optional
from django.db import models
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError
from .models import Category, Product
from vendors.models import Vendor

class MarketplaceService:
    @staticmethod
    def create_category(name: str, description: str = "", icon: Any = None) -> Category:
        """
        Create a new product category.
        """
        if Category.objects.filter(name=name).exists():
            raise ValidationError(f"Category '{name}' already exists.")
        
        return Category.objects.create(
            name=name,
            slug=slugify(name),
            description=description,
            icon=icon
        )

    @staticmethod
    def get_active_categories_with_counts():
        """
        Return active categories with the count of active products in each.
        """
        return Category.objects.filter(is_active=True).annotate(
            product_count=models.Count('products', filter=models.Q(products__is_active=True))
        ).order_by('-product_count', 'name')

    @staticmethod
    def add_product_to_marketplace(vendor: Vendor, data: Dict[str, Any]) -> Product:
        """
        Add a vendor product to the marketplace catalog.
        """
        category_id = data.get('category_id')
        if not category_id:
            raise ValidationError("Category ID is required.")
        
        try:
            category = Category.objects.get(id=category_id, is_active=True)
        except Category.DoesNotExist:
            raise ValidationError("Invalid or inactive category.")

        # Ensure slug uniqueness
        name = data.get('name')
        slug = slugify(name)
        original_slug = slug
        count = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{count}"
            count += 1

        product = Product.objects.create(
            vendor=vendor,
            category=category,
            slug=slug,
            **{k: v for k, v in data.items() if k not in ['category_id', 'slug']}
        )
        return product

    @staticmethod
    def update_marketplace_product(product_id: int, vendor: Vendor, data: Dict[str, Any]) -> Product:
        """
        Update an existing product by its vendor.
        """
        try:
            product = Product.objects.get(id=product_id, vendor=vendor)
        except Product.DoesNotExist:
            raise ValidationError("Product not found or access denied.")

        category_id = data.pop('category_id', None)
        if category_id:
            try:
                product.category = Category.objects.get(id=category_id, is_active=True)
            except Category.DoesNotExist:
                raise ValidationError("Invalid category.")

        # If name changes, we update the slug too (standard SEO practice)
        new_name = data.get('name')
        if new_name and new_name != product.name:
            product.name = new_name
            slug = slugify(new_name)
            original_slug = slug
            count = 1
            while Product.objects.filter(slug=slug).exclude(id=product_id).exists():
                slug = f"{original_slug}-{count}"
                count += 1
            product.slug = slug

        # Update other fields
        for attr, value in data.items():
            if attr not in ['slug']:
                setattr(product, attr, value)
        
        product.save()
        return product

    @staticmethod
    def get_marketplace_catalog(
        category_slug: Optional[str] = None, 
        vendor_id: Optional[int] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_featured: Optional[bool] = None
    ):
        """
        Retrieve products with optimized queries and advanced filtering.
        """
        queryset = Product.objects.filter(is_active=True).select_related('vendor', 'category')
        
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | 
                models.Q(description__icontains=search) |
                models.Q(category__name__icontains=search)
            )
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured)
            
        return queryset

    @staticmethod
    def get_featured_products(limit: int = 10):
        """
        Quick fetch for featured items.
        """
        return Product.objects.filter(
            is_active=True, 
            is_featured=True
        ).select_related('vendor', 'category')[:limit]

    @staticmethod
    def delete_marketplace_product(product_id: int, vendor: Vendor):
        """
        Delete a product.
        """
        try:
            product = Product.objects.get(id=product_id, vendor=vendor)
            product.delete()
            return True
        except Product.DoesNotExist:
            raise ValidationError("Product not found or access denied.")
