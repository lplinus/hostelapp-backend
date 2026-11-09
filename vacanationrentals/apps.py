from django.apps import AppConfig


class VacanationrentalsConfig(AppConfig):
    name = 'vacanationrentals'
    verbose_name = 'Vacation Rentals'

    def ready(self):
        try:
            import vacanationrentals.tasks  # noqa: F401
        except ImportError:
            pass
