"""
decorators.py — Decoradores personalizados de control de acceso (RBAC).

Implementa un sistema de Control de Acceso Basado en Roles (RBAC) sencillo
que trabaja en conjunto con @login_required de Django. Mientras @login_required
verifica que el usuario esté autenticado, @rol_requerido verifica que su rol
tenga permiso para acceder a esa vista concreta.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def rol_requerido(roles_permitidos=[]):
    """
    Decorador de fábrica que restringe el acceso a una vista según el rol.

    Uso:
        @rol_requerido(roles_permitidos=['secretaria', 'admin'])
        def mi_vista(request): ...

    Si el usuario tiene un rol no incluido en la lista, se le redirige
    al dashboard raíz con un mensaje de error (prevención de IDOR).

    Args:
        roles_permitidos (list): Roles de usuario autorizados a acceder.

    Returns:
        Callable: La vista ejecutada si el rol coincide, o un redirect seguro.
    """
    def decorator(view_func):
        @wraps(view_func)  # Preserva el nombre y docstring de la vista original
        def _wrapped_view(request, *args, **kwargs):
            if request.user.rol in roles_permitidos:
                return view_func(request, *args, **kwargs)
            # Intento de acceso no autorizado: registramos un aviso visual y redirigimos
            messages.error(request, "No tienes permiso para acceder a esta sección.")
            return redirect('inicio')
        return _wrapped_view
    return decorator