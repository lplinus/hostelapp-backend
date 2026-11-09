from django.apps import AppConfig


class HotelsConfig(AppConfig):
    name = 'hotels'

    def ready(self):
        try:
            import hotels.tasks  # noqa: F401
        except ImportError:
            pass
