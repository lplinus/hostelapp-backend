from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = 'orders'

    def ready(self):
        try:
            import orders.tasks  # noqa: F401
        except ImportError:
            pass
