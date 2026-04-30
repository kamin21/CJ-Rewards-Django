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
# El decorador personalizado rechaza el acceso si el rol no coincide
@rol_requerido(roles_permitidos=['alumno'])
def dashboard_alumno(request):
    """Vista principal (Resumen) del alumno."""
    username = request.user.username
    context = {
        'puntos': db_manager.obtener_puntos_alumno(username),
        'tareas_listas': len([t for t in db_manager.obtener_historial_puntos(username) if t.get('tipo') == 'Tarea Finalizada'])
    }
    # Nueva ruta: dashboards/alumno/alumno.html
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
    """Procesamiento de transacciones seguras con aviso de último stock."""
    resultado = db_manager.canjear_recompensa(request.user.username, recompensa_id)
    
    if type(resultado) == dict and resultado.get('exito'):
        # Comprueba la bandera 'fue_ultimo' para lanzar un aviso especial
        if resultado.get('fue_ultimo'):
            # El mensaje especial que querías
            messages.success(request, "¡Canje realizado con éxito! Te has llevado la ÚLTIMA unidad disponible. El premio ha sido retirado de la tienda.")
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
@login_required
@rol_requerido(roles_permitidos=['secretaria'])
def dashboard_secretaria(request):
    """Muestra el panel principal unificado con paginación."""
    # Catálogo normal
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
    total_usuarios = Usuario.objects.count()
    intentos_fallidos = len([l for l in logs if not l.get('exitoso')])
    
    context = {
        'logs_acceso': logs,
        'total_usuarios': total_usuarios,
        'intentos_fallidos': intentos_fallidos,
    }
    return render(request, 'dashboards/admin/admin.html', context)

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