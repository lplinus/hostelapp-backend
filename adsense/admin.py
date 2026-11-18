from django.contrib import admin
from .models import AdCampaign, AdPlan


@admin.register(AdPlan)
class AdPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "plan_code", "duration_days", "price", "is_popular", "is_active", "order")
    list_editable = ("price", "is_popular", "is_active", "order")
    list_filter = ("is_active", "is_popular")
    search_fields = ("name", "plan_code")


@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "campaign_name",
        "owner",
        "property_type",
        "ad_type",
        "placement",
        "status",
        "impressions_count",
        "clicks_count",
        "ctr_display",
        "budget",
        "days_remaining_display",
        "start_date",
        "end_date",
    )
    list_filter = ("status", "property_type", "ad_type", "placement", "is_deleted", "created_at")
    search_fields = (
        "campaign_name",
        "owner__username",
        "owner__email",
        "hotel__name",
        "vacation_rental__title",
    )
    readonly_fields = ("impressions_count", "clicks_count", "created_at", "updated_at")

    def ctr_display(self, obj):
        return f"{obj.ctr}%"
    ctr_display.short_description = "CTR"

    def days_remaining_display(self, obj):
        days = obj.days_remaining
        return f"{days} days" if days > 0 else "Expired"
    days_remaining_display.short_description = "Remaining"
