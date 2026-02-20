from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = "System Notifications"

    def ready(self):
        # Import signal handlers so they connect when the app is ready.
        import notifications.handlers  # noqa: F401
