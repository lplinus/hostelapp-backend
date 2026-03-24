from django.contrib import admin
from .models import RoomType, Bed


class BedInline(admin.TabularInline):
    model = Bed
    extra = 0
    fields = ("bed_number", "total_beds", "beds_available", "is_available")
    readonly_fields = ("bed_number",)

    def has_add_permission(self, request, obj=None):
        # Beds are managed via the serializer/API, not manually in admin
        return False


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ("hostel", "get_category", "get_sharing", "base_price", "price_per_day", "is_available", "get_total_beds", "get_available_beds")
    list_filter = ("hostel", "room_category", "sharing_type", "is_available")
    search_fields = ("hostel__name",)
    ordering = ("hostel__name", "room_category", "sharing_type")
    list_editable=("is_available",)
    inlines = [BedInline]

    def get_category(self, obj):
        return obj.get_room_category_display()
    get_category.short_description = "Category"

    def get_sharing(self, obj):
        return obj.get_sharing_type_display()
    get_sharing.short_description = "Sharing"

    def get_total_beds(self, obj):
        bed = obj.beds.first()
        if bed and bed.total_beds:
            return bed.total_beds
        return obj.beds.count()
    get_total_beds.short_description = "Total Beds"

    def get_available_beds(self, obj):
        bed = obj.beds.first()
        if bed and bed.beds_available is not None:
            return bed.beds_available
        return obj.beds.filter(is_available=True).count()
    get_available_beds.short_description = "Available"


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ("get_hostel", "get_room_type", "total_beds", "beds_available", "is_available")
    list_editable = ("is_available",)
    list_filter = ("room_type__hostel", "room_type__room_category", "is_available")
    search_fields = ("room_type__hostel__name",)
    ordering = ("room_type__hostel__name", "room_type__room_category", "room_type__sharing_type")

    def get_hostel(self, obj):
        return obj.room_type.hostel.name
    get_hostel.short_description = "Hostel"

    def get_room_type(self, obj):
        return f"{obj.room_type.get_room_category_display()} - {obj.room_type.get_sharing_type_display()}"
    get_room_type.short_description = "Room Type"