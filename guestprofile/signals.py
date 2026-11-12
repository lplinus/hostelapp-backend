from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import User
from .models import GuestProfile


@receiver(post_save, sender=User)
def create_or_update_guest_profile(sender, instance, created, **kwargs):
    """
    Automatically create or maintain a GuestProfile whenever a User is created or updated
    with role='guest' (or general users).
    """
    # Prevent signal from firing during loaddata / fixtures
    # if kwargs.get("raw", False):
    #     return
    if instance.role == "guest":
        profile, was_created = GuestProfile.objects.get_or_create(user=instance)
        # Keep basic profile data aligned with User table if modified
        updated_fields = []
        user_name = instance.get_full_name().strip() or instance.username
        if user_name and profile.full_name != user_name and not profile.full_name:
            profile.full_name = user_name
            updated_fields.append("full_name")
        if instance.email and profile.email != instance.email and not profile.email:
            profile.email = instance.email
            updated_fields.append("email")
        if getattr(instance, "phone", None) and profile.phone_number != instance.phone and not profile.phone_number:
            profile.phone_number = instance.phone
            updated_fields.append("phone_number")
        
        if updated_fields:
            profile.save(update_fields=updated_fields)

