from django.contrib import admin
from .models import TermsAndConditions, PrivacyPolicy


@admin.register(TermsAndConditions)
class TermsAdmin(admin.ModelAdmin):
    list_display = ("title", "effective_date", "updated_at")


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("title", "effective_date", "updated_at")