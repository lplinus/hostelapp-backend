from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookings'
    verbose_name = 'Hostel Bookings'

    def ready(self):
        try:
            import bookings.tasks  # noqa: F401
        except ImportError:
            pass
