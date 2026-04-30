from django.db.models.signals import post_save , post_delete
from django.dispatch import receiver
from .models import Usuario
import os
from django.conf import settings

# Importamos tu gestor de Firebase
from .gestor_firebase import GestorCJRewards

# Ruta absoluta al JSON de credenciales para evitar errores de ruta en el servidor
ruta_json = os.path.join(settings.BASE_DIR, 'Firebase_conf', 'CJ_Rewards_Credentials.json')
db_manager = GestorCJRewards(ruta_credenciales=ruta_json)

# @receiver 'escucha' el evento post_save del modelo Usuario. 
# Se ejecuta de fondo sin que el administrador tenga que hacer nada extra.
@receiver(post_save, sender=Usuario)
def sincronizar_usuario_con_firebase(sender, instance, created, **kwargs):
   # Este 'chivato' se activa automáticamente CADA VEZ que se guarda un Usuario.
   # La variable 'created' es True solo si es un usuario NUEVO (evita duplicados al editar).
    if created:
        try:
            # Usamos el ID o el username de Django como identificador único en Firebase
            uid_firebase = str(instance.username)
            
            # Llamamos a la función que creaste en tu gestor_firebase.py para inyectarlo en NoSQL
            db_manager.crear_usuario(
                uid=uid_firebase, 
                email=instance.email, 
                rol=instance.rol
            )
            print(f"Usuario '{instance.username}' copiado a Firebase.")
        except Exception as e:
            print(f"Error al sincronizar con Firebase: {e}")

# 'Escucha' cuando se borra un usuario del sistema relacional para mantener la integridad en la nube
@receiver(post_delete, sender=Usuario)
def eliminar_usuario_en_firebase(sender, instance, **kwargs):
    
    # Este 'chivato' se activa automáticamente CADA VEZ que se elimina un Usuario en Django.
    
    try:
        uid_firebase = str(instance.username)
        db_manager.eliminar_usuario(uid_firebase)
        print(f"¡Éxito! Usuario '{instance.username}' eliminado de Firebase.")
    except Exception as e:
        print(f"  Error al eliminar en Firebase: {e}")