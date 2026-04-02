from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'quantity_unit', 'stock', 'is_active')
    list_filter = ('category', 'is_active', 'is_featured', 'quantity_unit')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('category', 'vendor', 'name', 'slug', 'description', 'price', 'image')
        }),
        ('Quantity Settings', {
            'fields': ('quantity_unit', 'quantity_steps', 'stock')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
    )
    prepopulated_fields = {'slug': ('name',)}
