import firebase_admin
from firebase_admin import credentials, firestore

class GestorCJRewards:
    def __init__(self, ruta_credenciales='CJRewards/Firebase_conf/CJ_Rewards_Credentials.json'):
        """Inicializa la conexión con Firebase Cloud Firestore."""
        # Se comprueba si la app ya está inicializada para evitar errores de duplicidad en Vercel
        if not firebase_admin._apps:
            # Se carga el certificado JSON privado para establecer la conexión segura
            cred = credentials.Certificate(ruta_credenciales)
            firebase_admin.initialize_app(cred)
        # Se crea la instancia del cliente de base de datos
        self.db = firestore.client()

    # 1. Gestión de usuarios y sistema (Admin / Automático)

    def crear_usuario(self, uid, email, rol="alumno"):
        """Crea un usuario en la colección correspondiente con su saldo inicial."""
        # Se define la referencia al documento usando el ID único (username)
        usuario_ref = self.db.collection('usuarios').document(uid)
        # Se insertan los datos básicos. Todos empiezan con 0 puntos por seguridad
        usuario_ref.set({
            'email': email,
            'rol': rol,
            'puntos_acumulados': 0
        })
        return True

    def eliminar_usuario(self, uid):
        """Elimina un usuario de la colección en Firebase."""
        try:
            self.db.collection('usuarios').document(uid).delete()
            return True
        except Exception as e:
            print(f"Error al eliminar usuario en Firebase: {e}")
            return False

    # 2. Funciones para el rol: Alumno (Visualización y Acción)
    
    def obtener_puntos_alumno(self, alumno_id):
        """Devuelve el saldo actual de puntos de un alumno."""
        doc = self.db.collection('usuarios').document(alumno_id).get()
        if doc.exists:
            return doc.to_dict().get('puntos_acumulados', 0)
        return 0

    def obtener_historial_puntos(self, alumno_id):
        """Recupera el historial de méritos (notas y tareas) normalizado para el HTML."""
        try:
            historial = []
            # Parte A: Notas Académicas
            # Realiza una consulta (query) buscando notas asociadas a este alumno
            notas = self.db.collection('historial_notas').where('alumno_id', '==', alumno_id).stream()
            for doc in notas:
                d = doc.to_dict()
                historial.append({
                    'concepto': f"Nota en {d.get('asignatura')}",
                    'tipo': 'Nota Académica',
                    'puntos': d.get('puntos_generados', 0),
                    'fecha': 'Reciente'
                })

            # Parte B: Tareas Finalizadas
            # Filtra las tareas que este alumno ha completado y validado secretaría
            tareas = self.db.collection('tareas').where('alumno_asignado', '==', alumno_id).where('estado', '==', 'Finalizada').stream()
            for doc in tareas:
                d = doc.to_dict()
                historial.append({
                    'concepto': d.get('titulo'),
                    'tipo': 'Tarea Finalizada',
                    'puntos': d.get('puntos_otorgados', 0),
                    'fecha': 'Completada'
                })
            return historial
        except Exception as e:
            print(f"Error en historial: {e}")
            return []

    def obtener_tareas_mixtas_alumno(self, alumno_id):
        """Trae tareas públicas y las que el alumno ya tiene asignadas."""
        try:
            tareas = []
            # 1. Tareas que están libres para todos
            docs_disp = self.db.collection('tareas').where('estado', '==', 'Disponible').stream()
            for doc in docs_disp:
                d = doc.to_dict()
                d['id'] = doc.id
                d['puntos'] = d.get('puntos_otorgados') or 0
                tareas.append(d)

            # 2. Tareas que este alumno específico tiene en curso
            docs_proc = self.db.collection('tareas').where('alumno_asignado', '==', alumno_id).where('estado', '==', 'En proceso').stream()
            for doc in docs_proc:
                d = doc.to_dict()
                d['id'] = doc.id
                d['puntos'] = d.get('puntos_otorgados') or 0
                tareas.append(d)
            return tareas
        except Exception as e:
            print(f"Error en tareas mixtas: {e}")
            return []

    def asignar_tarea_a_alumno(self, tarea_id, alumno_id):
        """Permite al alumno solicitar una tarea y ponerse a trabajar."""
        tarea_ref = self.db.collection('tareas').document(tarea_id)

        # Usamos transacción para evitar que dos alumnos cojan la misma tarea a la vez
        @firestore.transactional
        def transaccion_asignar(transaction, t_ref):
            t_snap = t_ref.get(transaction=transaction)
            # Solo asignamos si existe y si su estado sigue siendo 'Disponible'
            if not t_snap.exists or t_snap.to_dict().get('estado') != 'Disponible':
                return False
                
            # Cambia el estado a "En proceso" para que desaparezca del tablón general
            transaction.update(t_ref, {
                'estado': 'En proceso',
                'alumno_asignado': alumno_id
            })
            return True

        try:
            return transaccion_asignar(self.db.transaction(), tarea_ref)
        except Exception as e:
            print(f"Error al asignar: {e}")
            return False

    def canjear_recompensa(self, alumno_id, recompensa_id):
        """Procesa el gasto, resta stock y elimina el premio si es el último."""
        alumno_ref = self.db.collection('usuarios').document(alumno_id)
        recompensa_ref = self.db.collection('recompensas').document(recompensa_id)

        # Usamos @firestore.transactional para asegurar que si algo falla, no se guarde nada a medias
        @firestore.transactional
        def transaccion_canje(transaction, a_ref, r_ref):
            # Obtenemos los datos actuales dentro de la transacción
            a_snap = a_ref.get(transaction=transaction)
            r_snap = r_ref.get(transaction=transaction)
            
            if not a_snap.exists or not r_snap.exists:
                return False

            puntos_alumno = a_snap.to_dict().get('puntos_acumulados', 0)
            datos_recomp = r_snap.to_dict()
            coste = datos_recomp.get('coste_puntos', 0)
            stock_actual = datos_recomp.get('stock')
            
            # Comprobaciones de seguridad en tiempo real (evita vulnerabilidades)
            if puntos_alumno < coste:
                return False
            if stock_actual is not None and stock_actual <= 0:
                return False

            # 1. Restar puntos al alumno de forma segura
            transaction.update(a_ref, {'puntos_acumulados': puntos_alumno - coste})
            
            fue_ultimo = False # Bandera para avisar a la vista HTML
            
            # 2. Gestionar el stock
            if stock_actual is not None:
                nuevo_stock = stock_actual - 1
                if nuevo_stock == 0:
                    # Si es el último en stock lo borramos de la base de datos automáticamente
                    transaction.delete(r_ref)
                    fue_ultimo = True
                else:
                    # Aún quedan, solo restamos 1 al stock
                    transaction.update(r_ref, {'stock': nuevo_stock})

            # 3. Guardar el "ticket" o recibo de auditoría
            canje_ref = self.db.collection('historial_canjeos').document()
            transaction.set(canje_ref, {
                'alumno_id': alumno_id,
                'recompensa_titulo': datos_recomp.get('titulo'),
                'puntos_gastados': coste,
                'fecha': "01/04/2026"
            })
            
            # Devolvemos un diccionario para darle más información a la vista
            return {'exito': True, 'fue_ultimo': fue_ultimo}

        try:
            return transaccion_canje(self.db.transaction(), alumno_ref, recompensa_ref)
        except Exception as e:
            print(f"Error en canjeo: {e}")
            return False

    def eliminar_recompensa(self, recompensa_id):
        """Permite a Secretaría borrar un premio manualmente del catálogo."""
        try:
            self.db.collection('recompensas').document(recompensa_id).delete()
            return True
        except Exception as e:
            print(f"Error al eliminar recompensa: {e}")
            return False

    def obtener_historial_canjeos(self, alumno_id):
        """Recupera el historial de premios canjeados por el alumno."""
        try:
            docs = self.db.collection('historial_canjeos').where('alumno_id', '==', alumno_id).stream()
            canjeos = []
            for doc in docs:
                d = doc.to_dict()
                canjeos.append({
                    'recompensa': d.get('recompensa_titulo'),
                    'puntos_gastados': d.get('puntos_gastados', 0),
                    'fecha': d.get('fecha', 'Reciente')
                })
            return canjeos
        except Exception as e:
            print(f"Error al obtener historial de canjeos: {e}")
            return []

    # 3. Funciones para el rol: Profesor (Notas)

    def procesar_nota_academica(self, alumno_id, asignatura, nota_numerica):
        """Convierte notas académicas en puntos de gamificación de forma atómica."""
        puntos_a_sumar = 0
        # Reglas de negocio para la conversión de notas a puntos
        if 9 <= nota_numerica <= 10: puntos_a_sumar = 10
        elif 7 <= nota_numerica <= 8: puntos_a_sumar = 5
        elif nota_numerica == 6: puntos_a_sumar = 2
            
        if puntos_a_sumar == 0: return False

        alumno_ref = self.db.collection('usuarios').document(alumno_id)
        
        # Transacción segura para sumar los puntos en tiempo real sin conflictos
        @firestore.transactional
        def transaccion_nota(transaction, a_ref):
            al_snap = a_ref.get(transaction=transaction)
            if al_snap.exists:
                # Validar que realmente sea un alumno (Prevención de manipulación IDOR del frontend)
                if al_snap.to_dict().get('rol') != 'alumno':
                    return False
                    
                pts_actuales = al_snap.to_dict().get('puntos_acumulados', 0)
                transaction.update(a_ref, {'puntos_acumulados': pts_actuales + puntos_a_sumar})

                historial_ref = self.db.collection('historial_notas').document()
                transaction.set(historial_ref, {
                    'alumno_id': alumno_id,
                    'asignatura': asignatura,
                    'nota': nota_numerica,
                    'puntos_generados': puntos_a_sumar
                })

        try:
            transaccion_nota(self.db.transaction(), alumno_ref)
            return puntos_a_sumar
        except Exception as e:
            print(f"Error procesando nota: {e}")
            return 0

    # 4. Funciones para el rol: Secretaría (Tareas y Premios)

    def crear_tarea(self, titulo, descripcion, puntos):
        """Añade una tarea al tablón de anuncios."""
        try:
            puntos_int = int(puntos)
            # Validación de seguridad: Evitar tareas que resten puntos
            if puntos_int <= 0:
                return False
                
            self.db.collection('tareas').add({
                'titulo': titulo,
                'descripcion': descripcion,
                'puntos_otorgados': puntos_int,
                'estado': 'Disponible',
                'alumno_asignado': None
            })
            return True
        except Exception as e:
            print(f"Error en crear_tarea: {e}")
            return False

    def crear_recompensa(self, titulo, coste, limite):
        """Añade un premio a la tienda con límite de unidades (stock)."""
        try:
            coste_int = int(coste)
            limite_int = int(limite)
            # Validación de seguridad: Evitar premios que regalen puntos (coste negativo)
            if coste_int <= 0 or limite_int < 0:
                return False
                
            self.db.collection('recompensas').add({
                'titulo': titulo,
                'coste_puntos': coste_int,
                'stock': limite_int
            })
            return True
        except Exception as e:
            print(f"Error en crear_recompensa: {e}")
            return False

    def obtener_tareas_por_estado(self, estado):
        """Filtra tareas para la tabla de validación (por ejemplo, 'En proceso')."""
        docs = self.db.collection('tareas').where('estado', '==', estado).stream()
        return [doc.to_dict() | {'id': doc.id} for doc in docs]

    def obtener_todas_las_tareas(self):
        """Trae todo para el monitor general de secretaría."""
        docs = self.db.collection('tareas').stream()
        return [doc.to_dict() | {'id': doc.id} for doc in docs]

    def validar_tarea(self, tarea_id):
        """Suma puntos al alumno y finaliza la tarea."""
        t_ref = self.db.collection('tareas').document(tarea_id)

        # Transacción segura para evitar problemas de sobreescritura de saldo
        @firestore.transactional
        def transaccion_validar(transaction, t_ref):
            t_snap = t_ref.get(transaction=transaction)
            if not t_snap.exists:
                return False
                
            t_doc = t_snap.to_dict()
            # Si ya estaba finalizada, no dar puntos dobles
            if t_doc.get('estado') == 'Finalizada':
                return False
                
            alumno_id = t_doc.get('alumno_asignado')
            puntos = t_doc.get('puntos_otorgados', 0)

            # Prevención de bug lógico: no validar ni gastar ciclos si la tarea no la tiene nadie
            if not alumno_id:
                return False

            if alumno_id:
                u_ref = self.db.collection('usuarios').document(alumno_id)
                u_snap = u_ref.get(transaction=transaction)
                pts_actuales = u_snap.to_dict().get('puntos_acumulados', 0) if u_snap.exists else 0

                # Actualiza el saldo y cierra el ciclo de vida de la tarea de forma atómica
                transaction.update(u_ref, {'puntos_acumulados': pts_actuales + puntos})
                transaction.update(t_ref, {'estado': 'Finalizada'})
                return True
            return False

        try:
            return transaccion_validar(self.db.transaction(), t_ref)
        except Exception as e:
            print(f"Error en validar_tarea: {e}")
            return False

    def marcar_tarea_incompleta(self, tarea_id):
        """Marca una tarea como no realizada y la devuelve al tablón (Rechazar)."""
        try:
            self.db.collection('tareas').document(tarea_id).update({
                'estado': 'Disponible',
                'alumno_asignado': None
            })
            return True
        except Exception:
            return False

    def eliminar_tarea(self, tarea_id):
        """Borra definitivamente una tarea del historial y de la base de datos."""
        try:
            self.db.collection('tareas').document(tarea_id).delete()
            return True
        except Exception:
            return False

    def obtener_historial_canjeos_global(self):
        """Trae todos los canjes de todos los alumnos para la auditoría de secretaría."""
        try:
            docs = self.db.collection('historial_canjeos').stream()
            return [doc.to_dict() | {'id': doc.id} for doc in docs]
        except Exception as e:
            print(f"Error al obtener historial global: {e}")
            return []

    # 5. Sistema de Logs de Seguridad (Sustituto de django-axes para Vercel)

    def registrar_intento_login(self, username, ip, exitoso=True):
        """Guarda un registro de cada intento de inicio de sesión en Firebase."""
        try:
            from datetime import datetime
            self.db.collection('logs_acceso').add({
                'usuario': username,
                'ip': ip,
                'exitoso': exitoso,
                'fecha': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'timestamp': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Error al registrar log de acceso: {e}")

    def obtener_logs_acceso(self, limite=50):
        """Recupera los últimos logs de acceso ordenados por fecha."""
        try:
            docs = self.db.collection('logs_acceso').order_by(
                'timestamp', direction=firestore.Query.DESCENDING
            ).limit(limite).stream()
            return [doc.to_dict() | {'id': doc.id} for doc in docs]
        except Exception as e:
            print(f"Error al obtener logs de acceso: {e}")
            return []