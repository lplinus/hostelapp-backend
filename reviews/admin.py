from django.contrib import admin
from .models import Review, HotelReview, VacationRentalReview


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("hostel", "user", "name", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("hostel__name", "user__username", "name", "comment")
    list_editable = ("is_approved",)


@admin.register(HotelReview)
class HotelReviewAdmin(admin.ModelAdmin):
    list_display = (
        "hotel",
        "user",
        "name",
        "rating",
        "cleanliness_rating",
        "comfort_rating",
        "service_rating",
        "location_rating",
        "is_approved",
        "created_at",
    )
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("hotel__name", "user__username", "name", "comment")
    list_editable = ("is_approved",)


@admin.register(VacationRentalReview)
class VacationRentalReviewAdmin(admin.ModelAdmin):
    list_display = (
        "rental",
        "user",
        "name",
        "rating",
        "cleanliness_rating",
        "accuracy_rating",
        "checkin_rating",
        "communication_rating",
        "location_rating",
        "value_rating",
        "is_approved",
        "created_at",
    )
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("rental__title", "user__username", "name", "comment")
    list_editable = ("is_approved",)
