import logging
import hashlib
from django.contrib.auth.backends import ModelBackend
from .models import Usuario
from .signals import get_db_manager

logger = logging.getLogger(__name__)

class FirebaseBackend(ModelBackend):
    """
    Backend de autenticación híbrido. 
    Permite el login incluso si la base de datos es de solo lectura.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 1. Intentar con el backend normal
        user = super().authenticate(request, username, password, **kwargs)
        if user:
            return user

        # 2. Si falla, verificar en Firebase (Texto Plano)
        try:
            db_manager = get_db_manager()
            doc = db_manager.db.collection('usuarios').document(username).get()
            
            if doc.exists:
                data = doc.to_dict()
                firebase_password = data.get('password')
                
                # Comparación en texto plano
                if str(firebase_password) == str(password):
                    try:
                        user = Usuario.objects.get(username=username)
                    except Usuario.DoesNotExist:
                        # Usuario virtual para Vercel
                        user = Usuario(
                            username=username,
                            email=data.get('email', ''),
                            rol=data.get('rol', 'alumno'),
                            is_active=True
                        )
                        # Generamos un ID determinista negativo basado en el username
                        # Esto permite que get_user lo recupere sin base de datos
                        user.id = int(hashlib.md5(username.encode()).hexdigest(), 16) % (10**8) * -1
                        
                    return user
        except Exception as e:
            logger.error(f"Error en FirebaseBackend: {e}")
            
        return None

    def get_user(self, user_id):
        # Si el ID es positivo, usar el método normal
        if user_id and user_id >= 0:
            try:
                return Usuario.objects.get(pk=user_id)
            except Usuario.DoesNotExist:
                return None
        
        # Si el ID es negativo, es un usuario virtual de Firebase (Vercel)
        if user_id and user_id < 0:
            try:
                db_manager = get_db_manager()
                # Buscamos en la colección de usuarios cuál coincide con este ID hash
                docs = db_manager.db.collection('usuarios').stream()
                for doc in docs:
                    username = doc.id
                    calc_id = int(hashlib.md5(username.encode()).hexdigest(), 16) % (10**8) * -1
                    if calc_id == user_id:
                        data = doc.to_dict()
                        user = Usuario(
                            username=username,
                            email=data.get('email', ''),
                            rol=data.get('rol', 'alumno'),
                            is_active=True
                        )
                        user.id = user_id
                        return user
            except Exception as e:
                logger.error(f"Error recuperando usuario virtual: {e}")
        
        return None
