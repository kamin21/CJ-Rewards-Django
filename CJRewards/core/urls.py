"""
core/urls.py — Tabla de enrutamiento de la aplicación principal.

Asigna cada URL a su vista correspondiente. Los patrones siguen una
convención semántica: /dashboard/<rol>/ para cada tipo de usuario.

Nota: Las acciones de admin usan el prefijo /dashboard/admin/ para evitar
colisiones con el enrutador nativo /admin/ de Django.
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- Autenticación ---
    # Login personalizado con registro de auditoría en Firebase
    path('login/', views.login_con_logs, name='login'),
    # Logout usa la vista nativa de Django redirigiendo a /login/ al salir
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # --- Raiz: Redirección inteligente post-login según el rol ---
    path('', views.redireccion_dashboard, name='inicio'),

    # --- Dashboard: Alumno ---
    path('dashboard/alumno/',          views.dashboard_alumno,    name='dashboard_alumno'),
    path('dashboard/alumno/puntos/',   views.alumno_puntos,       name='alumno_puntos'),
    path('dashboard/alumno/tareas/',   views.alumno_tareas,       name='alumno_tareas'),
    path('dashboard/alumno/tienda/',   views.catalogo_recompensas, name='catalogo_recompensas'),

    # --- Acciones del alumno (sin vista propia, redirigen tras ejecutar) ---
    path('solicitar-tarea/<str:tarea_id>/',       views.solicitar_tarea,       name='solicitar_tarea'),
    path('canjear-recompensa/<str:recompensa_id>/', views.canjear_recompensa,  name='canjear_recompensa'),

    # --- Dashboard: Profesor ---
    path('dashboard/profesor/', views.dashboard_profesor, name='dashboard_profesor'),

    # --- Dashboard: Secretaría ---
    path('dashboard/secretaria/',                              views.dashboard_secretaria,       name='dashboard_secretaria'),
    path('secretaria/crear-tarea/',                            views.crear_tarea_admin,          name='crear_tarea_admin'),
    path('secretaria/crear-recompensa/',                       views.crear_recompensa_admin,     name='crear_recompensa_admin'),
    path('secretaria/validar-tarea/',                          views.validar_tarea_admin,        name='validar_tarea_admin'),
    path('secretaria/eliminar-recompensa/<str:recompensa_id>/', views.eliminar_recompensa_admin, name='eliminar_recompensa_admin'),

    # --- Dashboard: Admin ---
    # Se usa el prefijo /dashboard/admin/ para no colisionar con /admin/ de Django
    path('dashboard/admin/',                                     views.dashboard_admin,          name='dashboard_admin'),
    path('dashboard/admin/crear-usuario/',                       views.crear_usuario_admin,      name='crear_usuario_admin'),
    path('dashboard/admin/eliminar-usuario/<int:usuario_id>/',   views.eliminar_usuario_admin,   name='eliminar_usuario_admin'),
]