from django.contrib import admin
from .models import Hostel, HostelImage, DefaultHostelImage, HostelTypeImage


@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    filter_horizontal = ("amenities",)
    list_display = ("name","owner","city","hostel_type", "price", "rating_avg", "is_active", "is_featured","is_toprated","is_verified","is_approved")
    list_filter = ("is_active", "is_featured", "city","is_toprated")
    search_fields = ("name", "slug")
    list_editable=("owner","is_toprated","is_featured","is_active","is_verified","is_approved")


@admin.register(HostelTypeImage)
class HostelTypeImageAdmin(admin.ModelAdmin):
    """
    Admin for HostelTypeImage.
    Only one record allowed — managed via Admin.
    """

    list_display = ("hostel_type", "image", "alt_text")
    list_filter = ("hostel_type",)
    search_fields = ("hostel_type", "alt_text")

    # def has_add_permission(self, request):
    #     # Only allow adding if no record exists
    #     return not HostelTypeImage.objects.exists()

    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(HostelImage)
class HostelImageAdmin(admin.ModelAdmin):
    list_display = ("hostel", "alt_text", "is_primary", "order")
    list_filter = ("hostel", "is_primary")


@admin.register(DefaultHostelImage)
class DefaultHostelImageAdmin(admin.ModelAdmin):
    """
    Singleton admin — only one record allowed.
    Upload fallback images here that will be shown for hostels with no images.
    """

    fieldsets = (
        (
            "Default Hostel Images",
            {
                "description": (
                    "Upload fallback images here. These will be shown when a hostel "
                    "has no images uploaded. You only need to create ONE record."
                ),
                "fields": ("image1", "image2", "image3", "image4", "image5", "image6", "image7", "image8", "image9", "image10","alt_text"),
            },
        ),
    )

    def has_add_permission(self, request):
        # Only allow adding if no record exists
        return not DefaultHostelImage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
