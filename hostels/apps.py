from django.apps import AppConfig


class HostelsConfig(AppConfig):
    name = 'hostels'

    def ready(self) -> None:
        import hostels.signals  # noqa: F401 — register signal handlers
