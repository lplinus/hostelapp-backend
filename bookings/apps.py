from django.apps import AppConfig


class BookingsConfig(AppConfig):
    name = 'bookings'

    def ready(self):
        try:
            import bookings.tasks  # noqa: F401
        except ImportError:
            pass
