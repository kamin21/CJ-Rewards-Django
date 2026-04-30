from django.shortcuts import redirect
from django.contrib import messages

def rol_requerido(roles_permitidos=[]):
    # Decorador personalizado para restringir el acceso según el rol del usuario.
    # Recibe una lista de roles (ej: ['alumno', 'profesor']) y evalúa el token de sesión.
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # Intercepta la petición HTTP y comprueba el atributo 'rol' del usuario activo
            if request.user.rol in roles_permitidos:
                # Si tiene el rol adecuado, le permite ejecutar la vista solicitada
                return view_func(request, *args, **kwargs)
            else:
                # Si es un intento de escalada de privilegios, bloquea y genera un log visual
                messages.error(request, "No tienes permiso para acceder a esta sección.")
                return redirect('inicio') # Redirige a su dashboard correspondiente de forma segura
        
        return _wrapped_view
    return decorator