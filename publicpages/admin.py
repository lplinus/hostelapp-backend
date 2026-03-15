from django.contrib import admin
from .models import (
    HomePage,
    WhyUsItem,
    About,
    AboutStat,
    AboutValue,
    AboutTeamMember,
    Contact,
    ContactInfo,
    ContactFAQ,
    ContactMessage,
    Pricing,
    PricingPlan,
    PricingFeature,
    PricingFAQ,
    LandingPage,
    LandingStat,
    LandingCityItem,
    LandingFeatureItem,
    LandingStepItem,
    LandingTestimonialItem,
)

admin.site.register(HomePage)
admin.site.register(WhyUsItem)
admin.site.register(About)
admin.site.register(AboutStat)
admin.site.register(AboutValue)
admin.site.register(AboutTeamMember)
admin.site.register(Contact)
admin.site.register(ContactInfo)
admin.site.register(ContactFAQ)
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "hostel", "is_read", "is_replied", "created_at")
    list_filter = ("is_read", "is_replied", "created_at", "hostel")
    search_fields = ("name", "email", "phone", "message")
    readonly_fields = ("created_at",)
    
    fieldsets = (
        ("Inquiry Details", {
            "fields": ("hostel", "name", "email", "phone", "message", "is_read", "created_at")
        }),
        ("Reply Information", {
            "fields": ("reply", "is_replied", "replied_at")
        }),
    )

    def save_model(self, request, obj, form, change):
        if change and obj.reply and not obj.is_replied:
            from django.utils import timezone
            from django.core.mail import send_mail
            from django.conf import settings

            if obj.email:
                try:
                    send_mail(
                        subject=f"Reply to your inquiry: {obj.name}",
                        message=obj.reply,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[obj.email],
                        fail_silently=False,
                    )
                    obj.is_replied = True
                    obj.replied_at = timezone.now()
                except Exception as e:
                    from django.contrib import messages
                    messages.error(request, f"Failed to send email: {str(e)}")
            else:
                # If only phone is available, we mark as replied (manual follow-up assumed)
                obj.is_replied = True
                obj.replied_at = timezone.now()
        
        super().save_model(request, obj, form, change)



        
admin.site.register(Pricing)
admin.site.register(PricingPlan)
admin.site.register(PricingFeature)
admin.site.register(PricingFAQ)
admin.site.register(LandingPage)
admin.site.register(LandingStat)
admin.site.register(LandingCityItem)
admin.site.register(LandingFeatureItem)
admin.site.register(LandingStepItem)
admin.site.register(LandingTestimonialItem)
