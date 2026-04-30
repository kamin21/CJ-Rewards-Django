from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Sistema de autenticación con registro de logs en Firebase
    path('login/', views.login_con_logs, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Redirección inteligente tras el login según el rol del usuario
    path('', views.redireccion_dashboard, name='inicio'),

    # Rutas del rol: alumno
    # Resumen general del alumno
    path('dashboard/alumno/', views.dashboard_alumno, name='dashboard_alumno'),
    
    # Vista detallada de puntos (Ingresos y Gastos)
    path('dashboard/alumno/puntos/', views.alumno_puntos, name='alumno_puntos'),
    
    # Tablón de actividades independientes
    path('dashboard/alumno/tareas/', views.alumno_tareas, name='alumno_tareas'),
    
    # Catálogo de premios (Tienda)
    path('dashboard/alumno/tienda/', views.catalogo_recompensas, name='catalogo_recompensas'),
    path('secretaria/eliminar-recompensa/<str:recompensa_id>/', views.eliminar_recompensa_admin, name='eliminar_recompensa_admin'),

    # Acciones lógicas (Procesamiento en Firebase)
    path('solicitar-tarea/<str:tarea_id>/', views.solicitar_tarea, name='solicitar_tarea'),
    path('canjear-recompensa/<str:recompensa_id>/', views.canjear_recompensa, name='canjear_recompensa'),

    # Rutas de otros roles (Dashboards)
    path('dashboard/profesor/', views.dashboard_profesor, name='dashboard_profesor'),
    path('dashboard/secretaria/', views.dashboard_secretaria, name='dashboard_secretaria'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),

    path('dashboard/secretaria/', views.dashboard_secretaria, name='dashboard_secretaria'),
    path('secretaria/crear-tarea/', views.crear_tarea_admin, name='crear_tarea_admin'),
    path('secretaria/crear-recompensa/', views.crear_recompensa_admin, name='crear_recompensa_admin'),
    path('secretaria/validar-tarea/', views.validar_tarea_admin, name='validar_tarea_admin'),
]