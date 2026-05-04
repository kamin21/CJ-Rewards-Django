from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from .models import Usuario
from .signals import get_db_manager

class UsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = ['username', 'email', 'rol', 'is_staff', 'is_active']
    actions = ['sincronizar_firebase']
    
    # Añadimos los campos extra a los formularios de edición y creación
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Rol', {'fields': ('rol',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información de Rol', {'fields': ('rol',)}),
    )

    @admin.action(description="Sincronizar usuarios seleccionados con Firebase")
    def sincronizar_firebase(self, request, queryset):
        """Acción masiva para asegurar que los usuarios existen en Firebase."""
        db_manager = get_db_manager()
        exitos = 0
        errores = 0
        
        for usuario in queryset:
            try:
                # Usamos set con merge=True para crear o actualizar sin borrar puntos
                usuario_ref = db_manager.db.collection('usuarios').document(str(usuario.username))
                usuario_ref.set({
                    'email': usuario.email,
                    'rol': usuario.rol,
                    # Si no existe, inicializamos puntos a 0. Si existe, no tocamos el campo.
                }, merge=True)
                
                # Verificamos si tiene puntos, si no, inicializamos solo si es nuevo
                doc = usuario_ref.get()
                if 'puntos_acumulados' not in doc.to_dict():
                    usuario_ref.update({'puntos_acumulados': 0})
                    
                exitos += 1
            except Exception:
                errores += 1
        
        if exitos:
            self.message_user(request, f"Se han sincronizado {exitos} usuarios con Firebase.", messages.SUCCESS)
        if errores:
            self.message_user(request, f"Hubo errores al sincronizar {errores} usuarios.", messages.ERROR)

# Registro seguro
try:
    admin.site.unregister(Usuario)
except admin.sites.NotRegistered:
    pass

admin.site.register(Usuario, UsuarioAdmin)