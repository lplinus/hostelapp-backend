from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("total_price",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "hostel",
        "vendor",
        "status",
        "order_type",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "order_type", "hostel", "vendor", "created_at")
    search_fields = (
        "hostel__name",
        "vendor__business_name",
        "id",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [OrderItemInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("hostel", "vendor")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "product",
        "product_name_at_order",
        "quantity",
        "unit_price",
        "total_price",
    )
    list_filter = ("order__status", "order__hostel", "order__vendor")
    search_fields = (
        "order__id",
        "product__name",
        "product_name_at_order",
    )
    readonly_fields = ("total_price",)
