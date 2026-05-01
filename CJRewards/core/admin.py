from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

class UsuarioAdmin(UserAdmin):
    # Configuración avanzada para gestionar el cifrado de contraseñas y el campo 'rol' desde el panel de administración.
    model = Usuario
    list_display = ['username', 'email', 'rol', 'is_staff', 'is_active']
    
    # Añadimos los campos extra a los formularios de edición y creación
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Rol', {'fields': ('rol',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información de Rol', {'fields': ('rol',)}),
    )

try:
    admin.site.unregister(Usuario)
except admin.sites.NotRegistered:
    pass # Si no estaba registrado, no hacemos nada y seguimos adelante

admin.site.register(Usuario, UsuarioAdmin)