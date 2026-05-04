import logging
import os
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Usuario

logger = logging.getLogger(__name__)

# Inicialización perezosa para evitar problemas en Vercel
_db_manager = None

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        from .gestor_firebase import GestorCJRewards
        ruta_json = os.path.join(settings.BASE_DIR, 'Firebase_conf', 'CJ_Rewards_Credentials.json')
        _db_manager = GestorCJRewards(ruta_credenciales=ruta_json)
    return _db_manager

@receiver(post_save, sender=Usuario)
def sincronizar_usuario_con_firebase(sender, instance, created, **kwargs):
    """Sincroniza el usuario con Firebase al crear o editar."""
    try:
        db_manager = get_db_manager()
        uid = str(instance.username)
        
        if created:
            db_manager.crear_usuario(
                uid=uid, 
                email=instance.email, 
                rol=instance.rol,
                password_hash=instance.password,
                first_name=instance.first_name,
                last_name=instance.last_name
            )

            logger.info(f"Usuario {uid} creado en Firebase via signal.")
        else:
            # Si ya existe, actualizamos usando merge para no borrar puntos
            usuario_ref = db_manager.db.collection('usuarios').document(uid)
            usuario_ref.set({
                'email': instance.email,
                'rol': instance.rol
            }, merge=True)
            logger.info(f"Usuario {uid} actualizado en Firebase via signal.")
    except Exception as e:
        logger.error(f"Error sincronizando {instance.username} con Firebase: {e}")

@receiver(post_delete, sender=Usuario)
def eliminar_usuario_en_firebase(sender, instance, **kwargs):
    """Elimina al usuario de Firebase al borrarlo de Django."""
    try:
        db_manager = get_db_manager()
        uid = str(instance.username)
        db_manager.liberar_tareas_usuario(uid)
        db_manager.eliminar_usuario(uid)
        logger.info(f"Usuario {uid} eliminado de Firebase via signal.")
    except Exception as e:
        logger.error(f"Error eliminando {instance.username} de Firebase: {e}")