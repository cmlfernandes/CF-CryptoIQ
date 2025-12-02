from django.apps import AppConfig


class CryptosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cryptos'

    def ready(self):
        """Start background tasks when app is ready"""
        import os
        # Only start background tasks if not in migration or test mode
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from cryptos.services.background_tasks import BackgroundTaskManager
                task_manager = BackgroundTaskManager()
                task_manager.start()
            except Exception as e:
                print(f"Warning: Could not start background tasks: {e}")