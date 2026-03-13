from django.contrib import admin
from .models import TermsAndConditions, PrivacyPolicy,FAQCategory,FAQ


@admin.register(TermsAndConditions)
class TermsAdmin(admin.ModelAdmin):
    list_display = ("title", "effective_date", "updated_at")


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("title", "effective_date", "updated_at")



@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "order", "is_active", "view_count")
    list_editable = ("category", "order", "is_active")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("question", "answer", "meta_title", "meta_description")
    prepopulated_fields = {"slug": ("question",)}
    readonly_fields = ("view_count", "created_at", "updated_at")