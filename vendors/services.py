from typing import Any, Dict, Optional
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError
from .models import Vendor
from marketplace.models import Product
from accounts.models import User

class VendorService:
    @staticmethod
    def create_vendor(owner: User, data: Dict[str, Any]) -> Vendor:
        """
        Create a new vendor profile for a user.
        Validates that the user is a vendor and doesn't already have a profile.
        """
        if owner.role != 'vendor':
            raise ValidationError("User must have the 'vendor' role.")
        
        if Vendor.objects.filter(owner=owner).exists():
            raise ValidationError("This user already has a vendor profile.")
        
        # Auto-generate slug if not provided, else slugify name
        business_name = data.get('business_name')
        if not business_name:
            raise ValidationError("Business name is required.")
        
        slug = slugify(business_name)
        # Ensure slug uniqueness
        original_slug = slug
        count = 1
        while Vendor.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{count}"
            count += 1
        
        data['slug'] = slug
        vendor = Vendor.objects.create(owner=owner, **data)
        return vendor

    @staticmethod
    def update_vendor(vendor: Vendor, data: Dict[str, Any]) -> Vendor:
        """
        Update vendor details.
        """
        for attr, value in data.items():
            if attr == 'business_name' and value != vendor.business_name:
                # Optionally re-generate slug? Often better to keep slug stable.
                pass
            setattr(vendor, attr, value)
        
        vendor.save()
        return vendor

    @staticmethod
    def add_product(vendor: Vendor, data: Dict[str, Any]) -> Product:
        """
        Add a product to a vendor's catalog.
        """
        return Product.objects.create(vendor=vendor, **data)

    @staticmethod
    def list_public_vendors(search: Optional[str] = None):
        """
        Return active vendors for marketplace.
        """
        queryset = Vendor.objects.filter(is_active=True)
        if search:
            queryset = queryset.filter(business_name__icontains=search)
        return queryset.prefetch_related('products')

    @staticmethod
    def get_vendor_catalog(vendor_id: int):
        """
        Retrieve available products for a specific vendor.
        """
        return Product.objects.filter(vendor_id=vendor_id, is_available=True)
