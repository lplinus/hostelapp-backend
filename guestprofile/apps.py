from django.apps import AppConfig


class GuestprofileConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "guestprofile"
    verbose_name = "Guests"

    def ready(self):
        import guestprofile.signals
