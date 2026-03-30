from django.contrib import admin
from .models import Vendor

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("business_name", "vendor_types", "owner", "contact_phone", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("business_name", "owner__username", "contact_phone", "contact_email")
    prepopulated_fields = {"slug": ("business_name",)}
