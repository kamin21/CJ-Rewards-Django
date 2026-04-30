from django.contrib import admin
from django.urls import path, include
from core import views

# Importaciones clave para modificar el comportamiento base de Django en producción
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import update_last_login

# DESCONEXIÓN CRÍTICA PARA SERVERLESS: 
# Evita que Django intente escribir el campo "last_login" en la base de datos de solo lectura de Vercel
user_logged_in.disconnect(update_last_login, dispatch_uid="update_last_login")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('secretaria/tarea/incompleta/', views.marcar_tarea_incompleta_admin, name='marcar_tarea_incompleta_admin'),
    path('secretaria/tarea/eliminar/<str:tarea_id>/', views.eliminar_tarea_admin, name='eliminar_tarea_admin'),
]