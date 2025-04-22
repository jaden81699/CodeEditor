from django.apps import AppConfig


class EditorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'editor'

    def ready(self):
        # This import makes sure the signal handlers are registered
        import editor.signals