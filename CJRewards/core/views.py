"""
views.py — Controladores HTTP de la aplicación CJ-Rewards.

Cada función recibe un HttpRequest de Django y devuelve un HttpResponse
(normalmente renderizando un template HTML o redirigiendo a otra URL).

Arquitectura de seguridad por capas:
  1. @login_required  → Verifica que el usuario haya iniciado sesión.
  2. @rol_requerido   → Verifica que su rol tenga acceso a esa sección.
  3. Lógica interna   → Comprueba la integridad de los datos antes de actuar.

Flujo de datos: Request → View → GestorCJRewards (Firebase) → Template.
"""
import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator

# Importaciones locales
from .models import Usuario
from .decorators import rol_requerido
from .gestor_firebase import GestorCJRewards

# 1. Configuración e Inicialización

# Se construye la ruta absoluta para el JSON de credenciales y se instancia el gestor
ruta_json = os.path.join(settings.BASE_DIR, 'Firebase_conf', 'CJ_Rewards_Credentials.json')
db_manager = GestorCJRewards(ruta_credenciales=ruta_json)

# @login_required garantiza que nadie no logueado pase de aquí
@login_required(login_url='/login/')
def redireccion_dashboard(request):
    """Controlador de tráfico que envía al usuario a su carpeta correspondiente."""
    # Lee el rol asociado al token del usuario activo
    rol = request.user.rol
    
    # Enrutamiento semántico según el RBAC
    if rol == 'alumno':
        return redirect('dashboard_alumno')
    elif rol == 'profesor':
        return redirect('dashboard_profesor')
    elif rol == 'secretaria':
        return redirect('dashboard_secretaria')
    elif rol == 'admin':
        return redirect('dashboard_admin')
    else:
        return redirect('login')

# 2. Vistas del Rol: Alumno (Carpeta: dashboards/alumno/)

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['alumno'])
def dashboard_alumno(request):
    """
    Vista principal del alumno: muestra su saldo actual y un contador rápido
    de tareas completadas para el resumen del dashboard.
    """
    username = request.user.username
    historial = db_manager.obtener_historial_puntos(username)
    context = {
        'puntos': db_manager.obtener_puntos_alumno(username),
        'tareas_listas': sum(1 for t in historial if t.get('tipo') == 'Tarea Finalizada')
    }
    return render(request, 'dashboards/alumno/alumno.html', context)

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['alumno'])
def alumno_puntos(request):
    """Vista detallada de economía: ingresos y gastos."""
    username = request.user.username
    context = {
        'puntos_actuales': db_manager.obtener_puntos_alumno(username),
        'historial_ganados': db_manager.obtener_historial_puntos(username),
        'historial_gastados': db_manager.obtener_historial_canjeos(username),
    }
    # Nueva ruta: dashboards/alumno/alumno_puntos.html
    return render(request, 'dashboards/alumno/alumno_puntos.html', context)

@login_required
@rol_requerido(roles_permitidos=['alumno'])
def alumno_tareas(request):
    """Carga tareas públicas y personales en la misma lista."""
    username = request.user.username
    context = {
        # Usamos la nueva función mixta para no sobrecargar el frontend
        'tareas_disponibles': db_manager.obtener_tareas_mixtas_alumno(username),
    }
    return render(request, 'dashboards/alumno/alumno_tareas.html', context)

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['alumno'])
def solicitar_tarea(request, tarea_id):
    """Asigna una tarea al alumno en Firebase."""
    username = request.user.username
    # Utiliza el módulo messages para enviar alertas (flash messages) a la vista
    if db_manager.asignar_tarea_a_alumno(tarea_id, username):
        messages.success(request, "¡Tarea solicitada! Ya aparece en tu gestión.")
    else:
        messages.error(request, "No se pudo solicitar la tarea.")
    return redirect('alumno_tareas')

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['alumno'])
def catalogo_recompensas(request):
    """Vista de la tienda de premios."""
    recompensas = db_manager.db.collection('recompensas').stream()
    lista_premios = [doc.to_dict() | {'id': doc.id} for doc in recompensas]
    
    context = {
        'puntos': db_manager.obtener_puntos_alumno(request.user.username),
        'recompensas': lista_premios
    }
    # Nueva ruta: dashboards/alumno/alumno_tienda.html
    return render(request, 'dashboards/alumno/alumno_tienda.html', context)

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['alumno'])
def canjear_recompensa(request, recompensa_id):
    """
    Procesa un canje de puntos. La lógica transaccional (comprobar saldo,
    restar puntos, decrementar stock) ocurre en gestor_firebase.py.
    Si fue el último item del stock, muestra un aviso especial al alumno.
    """
    resultado = db_manager.canjear_recompensa(request.user.username, recompensa_id)

    if isinstance(resultado, dict) and resultado.get('exito'):
        if resultado.get('fue_ultimo'):
            messages.success(request, "¡Canje realizado! Te has llevado la ÚLTIMA unidad. El premio ha sido retirado de la tienda.")
        else:
            messages.success(request, "¡Canje realizado con éxito!")
    else:
        messages.error(request, "Saldo insuficiente, error en el sistema o recompensa ya agotada.")

    return redirect('catalogo_recompensas')

# 3. Vistas del Rol: Profesor (Carpeta: dashboards/profesor/)

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['profesor'])
def dashboard_profesor(request):
    """Gestión académica de notas."""
    # Extrae solo los alumnos de la BD relacional para listarlos en el formulario
    alumnos = Usuario.objects.filter(rol='alumno')

    if request.method == 'POST':
        alumno_id = request.POST.get('alumno_id')
        asignatura = request.POST.get('asignatura')
        nota = float(request.POST.get('nota'))

        puntos_ganados = db_manager.procesar_nota_academica(alumno_id, asignatura, nota)
        if puntos_ganados:
            messages.success(request, f"¡Nota guardada! Sumados {puntos_ganados} pts.")
        else:
            messages.warning(request, "Nota guardada, pero no suma puntos.")
            
        return redirect('dashboard_profesor')

    # Nueva ruta: dashboards/profesor/profesor.html
    return render(request, 'dashboards/profesor/profesor.html', {'alumnos': alumnos})

# 4. Vistas del Rol: Secretaría (Carpeta: dashboards/secretaria/)

@login_required
@rol_requerido(roles_permitidos=['secretaria'])
def dashboard_secretaria(request):
    """
    Panel principal de secretaría. Agrega en una sola página:
      - Todas las tareas (paginadas de 10 en 10).
      - El historial global de canjeos (paginado de 10 en 10).
      - Las tareas pendientes de validar ('En proceso').
      - El catálogo actual de recompensas.

    Se usa el Paginator de Django para no cargar en memoria listas
    muy grandes de un solo golpe.
    """
    recompensas = db_manager.db.collection('recompensas').stream()
    lista_premios = [doc.to_dict() | {'id': doc.id} for doc in recompensas]
    
    # Implementa Paginator de Django para no saturar la memoria con el histórico
    lista_todas_tareas = db_manager.obtener_todas_las_tareas()
    paginator_tareas = Paginator(lista_todas_tareas, 10) # 10 elementos por página
    page_number_tareas = request.GET.get('page_tareas')
    todas_paginadas = paginator_tareas.get_page(page_number_tareas)

    lista_canjeos = db_manager.obtener_historial_canjeos_global()
    paginator_canjeos = Paginator(lista_canjeos, 10) # 10 elementos por página
    page_number_canjeos = request.GET.get('page_canjeos')
    canjeos_paginados = paginator_canjeos.get_page(page_number_canjeos)
    
    context = {
        'pendientes': db_manager.obtener_tareas_por_estado('En proceso'),
        'todas': todas_paginadas,  # Enviamos la versión cortada en páginas
        'catalogo': lista_premios,
        'canjeos_globales': canjeos_paginados # Enviamos la versión cortada en páginas
    }
    return render(request, 'dashboards/secretaria/secretaria.html', context)

@login_required
@rol_requerido(roles_permitidos=['secretaria'])
def crear_tarea_admin(request):
    """Solo crea tareas."""
    if request.method == 'POST':
        if db_manager.crear_tarea(request.POST.get('titulo_tarea'), request.POST.get('desc_tarea'), request.POST.get('puntos_tarea')):
            messages.success(request, "Tarea publicada correctamente.")
        else:
            messages.error(request, "Error al crear tarea. Asegúrate de que los puntos sean mayores que 0.")
    return redirect('dashboard_secretaria')

@login_required
@rol_requerido(roles_permitidos=['secretaria'])
def crear_recompensa_admin(request):
    """Solo crea premios con límite de stock."""
    if request.method == 'POST':
        titulo = request.POST.get('titulo_recompensa')
        coste = request.POST.get('coste_recompensa')
        limite = request.POST.get('limite_recompensa') # Captura el nuevo input
        
        if db_manager.crear_recompensa(titulo, coste, limite):
            messages.success(request, f"Premio '{titulo}' creado con {limite} uds disponibles.")
        else:
            messages.error(request, "Error al crear premio. Comprueba que el coste y stock sean válidos (mayores que 0).")
    return redirect('dashboard_secretaria')

@login_required
@rol_requerido(roles_permitidos=['secretaria'])
def validar_tarea_admin(request):
    """Otorga puntos."""
    if request.method == 'POST':
        if db_manager.validar_tarea(request.POST.get('tarea_id')):
            messages.success(request, "Puntos otorgados al alumno.")
        else:
            messages.error(request, "No se ha podido validar la tarea.")
    return redirect('dashboard_secretaria')

@login_required
@rol_requerido(roles_permitidos=['secretaria'])
def eliminar_recompensa_admin(request, recompensa_id):
    """Permite borrar una recompensa desde el panel."""
    if request.method == 'POST':
        if db_manager.eliminar_recompensa(recompensa_id):
            messages.success(request, "Recompensa eliminada de la tienda.")
        else:
            messages.error(request, "No se pudo eliminar la recompensa.")
    return redirect('dashboard_secretaria')

@login_required
@rol_requerido(roles_permitidos=['secretaria'])
def marcar_tarea_incompleta_admin(request):
    """Rechaza una tarea y la devuelve al tablón disponible."""
    if request.method == 'POST':
        tarea_id = request.POST.get('tarea_id')
        if db_manager.marcar_tarea_incompleta(tarea_id):
            messages.warning(request, "Tarea marcada como incompleta. Vuelve a estar disponible para el alumnado.")
        else:
            messages.error(request, "Error al actualizar la tarea.")
    return redirect('dashboard_secretaria')

@login_required
@rol_requerido(roles_permitidos=['secretaria'])
def eliminar_tarea_admin(request, tarea_id):
    """Elimina una tarea por completo del historial."""
    if request.method == 'POST':
        if db_manager.eliminar_tarea(tarea_id):
            messages.success(request, "Tarea eliminada del historial permanentemente.")
        else:
            messages.error(request, "Error al eliminar la tarea.")
    return redirect('dashboard_secretaria')

# 5. Vistas del Rol: Admin (Carpeta: dashboards/admin/)

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['admin'])
def dashboard_admin(request):
    """Control global del sistema con logs de seguridad desde Firebase."""
    logs = db_manager.obtener_logs_acceso(limite=50)
    usuarios = Usuario.objects.all().order_by('-id')
    total_usuarios = usuarios.count()
    intentos_fallidos = len([l for l in logs if not l.get('exitoso')])
    
    context = {
        'logs_acceso': logs,
        'usuarios': usuarios,
        'total_usuarios': total_usuarios,
        'intentos_fallidos': intentos_fallidos,
    }
    return render(request, 'dashboards/admin/admin.html', context)

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['admin'])
def crear_usuario_admin(request):
    """
    Crea un usuario en Django (SQLite) y lo sincroniza con Firebase.

    El usuario se instancia en memoria primero, se le aplica la contraseña
    hasheada y se guarda con un único INSERT a la base de datos (optimizado
    para reducir operaciones en SQLite en Vercel).
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        email    = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name  = request.POST.get('last_name')
        rol        = request.POST.get('rol')

        try:
            if Usuario.objects.filter(username=username).exists():
                messages.error(request, "El nombre de usuario ya existe.")
            else:
                # Instanciar en memoria, hashear la contraseña y un único save()
                user = Usuario(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    rol=rol
                )
                user.set_password(password)
                user.save()

                # Sincronizar el registro también en Firebase
                db_manager.crear_usuario(username, email, rol)

                messages.success(request, f"Usuario {username} creado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al crear usuario: {e}")

    return redirect('dashboard_admin')

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['admin'])
def eliminar_usuario_admin(request, usuario_id):
    """
    Elimina un usuario del sistema de forma consistente en tres pasos:
      1. Libera sus tareas en Firebase (vuelven a estado 'Disponible').
      2. Borra su documento de la colección 'usuarios' en Firestore.
      3. Elimina su cuenta del sistema de autenticación de Django (SQLite).

    El orden es importante: si Django fallara en el paso 3, Firebase ya
    estaría limpio. El proceso no elimina el historial de notas ni de
    canjeos para mantener la trazabilidad de auditoría.
    """
    if request.method == 'POST':
        try:
            user = Usuario.objects.get(id=usuario_id)
            username = user.username

            db_manager.liberar_tareas_usuario(username)   # Paso 1
            db_manager.eliminar_usuario(username)         # Paso 2
            user.delete()                                 # Paso 3

            messages.success(request, f"Usuario {username} eliminado exitosamente.")
        except Usuario.DoesNotExist:
            messages.error(request, "El usuario no existe.")
        except Exception as e:
            messages.error(request, f"Error al eliminar usuario: {e}")

    return redirect('dashboard_admin')

# 6. Login personalizado con registro de logs en Firebase

def login_con_logs(request):
    """Vista de login que registra cada intento (exitoso o fallido) en Firebase."""
    if request.user.is_authenticated:
        return redirect('inicio')
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        # Obtener la IP real del usuario (compatible con proxies y Vercel)
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', 'Desconocida')
        
        # --- NUEVO: RATE LIMITING ---
        if not db_manager.comprobar_rate_limit(ip, limite=5, minutos=10):
            messages.error(request, "Cuenta bloqueada temporalmente por demasiados intentos fallidos. Inténtalo de nuevo en 10 minutos.")
            from django.contrib.auth.forms import AuthenticationForm
            return render(request, 'login.html', {'form': AuthenticationForm(request, data=request.POST)})
        # ----------------------------
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Registrar acceso exitoso en Firebase
            try:
                db_manager.registrar_intento_login(username, ip, exitoso=True)
            except Exception:
                pass  # No bloquear el login si Firebase falla
            return redirect('inicio')
        else:
            # Registrar intento fallido en Firebase
            try:
                db_manager.registrar_intento_login(username, ip, exitoso=False)
            except Exception:
                pass
            # Pasar un formulario con errores para que el template muestre el mensaje
            from django.contrib.auth.forms import AuthenticationForm
            form = AuthenticationForm(request, data=request.POST)
            form.is_valid()  # Forzar validación para generar errores
            return render(request, 'login.html', {'form': form})
    
    from django.contrib.auth.forms import AuthenticationForm
    return render(request, 'login.html', {'form': AuthenticationForm()})