from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    # Añadimos esta función ready() para cargar los signals
    def ready(self):
        import core.signals
        
        # Parche para Vercel: Evita el Error 500 al no intentar guardar la fecha del último login
        # Los imports se hacen aquí dentro para no provocar errores de carga prematura
        if 'VERCEL' in os.environ or not os.environ.get('DEBUG', 'False') == 'True':
            from django.contrib.auth.signals import user_logged_in
            from django.contrib.auth.models import update_last_login
            user_logged_in.disconnect(update_last_login, dispatch_uid='update_last_login')