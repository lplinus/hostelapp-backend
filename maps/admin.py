from django.contrib import admin
from Hbackend.base_models import SoftDeleteAdmin
from .models import PropertyPinpoint, MapPlace


@admin.register(MapPlace)
class MapPlaceAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "city",
        "landmark",
        "latitude",
        "longitude",
        "is_active",
        "is_featured",
        "updated_at",
    ]
    list_filter = ["category", "is_active", "is_featured", "city"]
    search_fields = ["title", "description", "landmark", "address", "city"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PropertyPinpoint)
class PropertyPinpointAdmin(SoftDeleteAdmin):
    list_display = [
        "title",
        "property_type",
        "property_id",
        "owner",
        "latitude",
        "longitude",
        "is_auto_fetched",
        "is_verified",
        "updated_at",
    ]
    list_filter = ["property_type", "is_auto_fetched", "is_verified", "is_deleted"]
    search_fields = ["title", "formatted_address", "landmark", "city", "area"]
    readonly_fields = ["created_at", "updated_at"]
