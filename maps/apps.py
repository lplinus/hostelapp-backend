from django.apps import AppConfig


class MapsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "maps"
    verbose_name = "Offline Maps & Location Pinpoint"

    def ready(self):
        from .signals import register_maps_signals
        register_maps_signals()
