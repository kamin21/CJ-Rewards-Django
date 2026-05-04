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
    """Gestión académica de notas. Incluye alumnos de SQLite y Firebase."""
    # 1. Alumnos de SQLite
    alumnos_dj = list(Usuario.objects.filter(rol='alumno'))
    usernames_dj = {u.username for u in alumnos_dj}
    
    # 2. Alumnos de Firebase (Vercel)
    alumnos_combinados = alumnos_dj
    try:
        # Buscamos en Firebase usuarios con rol 'alumno' que no estén en SQLite
        docs = db_manager.db.collection('usuarios').where('rol', '==', 'alumno').stream()
        for doc in docs:
            username = doc.id
            if username not in usernames_dj:
                # Objeto simple para el select del template
                alumnos_combinados.append({'username': username})
    except Exception as e:
        print(f"Error al traer alumnos de Firebase: {e}")

    if request.method == 'POST':
        alumno_id = request.POST.get('alumno_id') # Es el username
        asignatura = request.POST.get('asignatura')
        nota = float(request.POST.get('nota'))

        puntos_ganados = db_manager.procesar_nota_academica(alumno_id, asignatura, nota)
        if puntos_ganados:
            messages.success(request, "¡Nota guardada correctamente!")
        else:
            messages.warning(request, "Nota guardada correctamente.")
            
        return redirect('dashboard_profesor')

    return render(request, 'dashboards/profesor/profesor.html', {'alumnos': alumnos_combinados})


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
    """
    Control global del sistema. 
    Combina usuarios de SQLite y Firebase para asegurar que todos sean visibles en Vercel.
    """
    logs = db_manager.obtener_logs_acceso(limite=50)
    
    # 1. Obtener usuarios de SQLite
    usuarios_dj = list(Usuario.objects.all())
    usernames_dj = {u.username for u in usuarios_dj}
    
    # 2. Obtener usuarios de Firebase que no estén en SQLite
    usuarios_combinados = usuarios_dj
    
    class VirtualUser:
        def __init__(self, username, email, rol, first_name="", last_name=""):
            self.username = username
            self.email = email
            self.rol = rol
            self.first_name = first_name
            self.last_name = last_name
            self.is_active = True
            self.is_staff = (rol == 'admin')
        def get_rol_display(self):
            roles_dict = dict(Usuario.ROLES)
            return roles_dict.get(self.rol, self.rol)

    try:
        docs = db_manager.db.collection('usuarios').stream()
        for doc in docs:
            data = doc.to_dict()
            username = doc.id
            if username not in usernames_dj:
                usuarios_combinados.append(VirtualUser(
                    username=username,
                    email=data.get('email', 'N/A'),
                    rol=data.get('rol', 'alumno'),
                    first_name=data.get('first_name', ''),
                    last_name=data.get('last_name', '')
                ))
    except Exception as e:
        print(f"Error al traer usuarios de Firebase: {e}")

    total_usuarios = len(usuarios_combinados)
    intentos_fallidos = len([l for l in logs if not l.get('exitoso')])
    
    context = {
        'logs_acceso': logs,
        'usuarios': usuarios_combinados,
        'total_usuarios': total_usuarios,
        'intentos_fallidos': intentos_fallidos,
    }
    return render(request, 'dashboards/admin/admin.html', context)


@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['admin'])
def crear_usuario_admin(request):
    """Crea un usuario en el sistema con contraseña en texto plano para Firebase."""
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
                user = Usuario(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    rol=rol
                )
                # Guardamos la contraseña en TEXTO PLANO según solicitado
                user.password = password 
                try:
                    user.save()
                    messages.success(request, "Usuario creado correctamente.")
                except Exception:
                    # Fallback para Vercel
                    from .signals import get_db_manager
                    manager = get_db_manager()
                    manager.crear_usuario(
                        uid=username, 
                        email=email, 
                        rol=rol, 
                        password_hash=password,
                        first_name=first_name,
                        last_name=last_name
                    )
                    messages.success(request, "Usuario creado correctamente.")

        except Exception as e:
            messages.error(request, f"Error al crear usuario: {e}")

    return redirect('dashboard_admin')

@login_required(login_url='/login/')
@rol_requerido(roles_permitidos=['admin'])
def eliminar_usuario_admin(request, username):
    """
    Elimina un usuario del sistema (Django y Firebase).
    Soporta eliminación por username para usuarios virtuales de Firebase.
    """
    if request.method == 'POST':
        try:
            # 1. Intentar borrar de Django (SQLite) si existe
            try:
                user = Usuario.objects.get(username=username)
                user.delete()
                messages.success(request, "Usuario eliminado correctamente.")
            except (Usuario.DoesNotExist, Exception):
                # 2. Si no existe en SQLite o es de solo lectura, borrar de Firebase
                from .signals import get_db_manager
                manager = get_db_manager()
                manager.liberar_tareas_usuario(username)
                manager.eliminar_usuario(username)
                messages.success(request, "Usuario eliminado correctamente.")


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