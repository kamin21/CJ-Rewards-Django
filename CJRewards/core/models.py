from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    # Modelo de usuario personalizado que extiende el de Django.
    # Almacena el rol y los puntos acumulados para mantener consistencia.
    
    # Tupla que define los roles restrictivos del sistema (RBAC)
    ROLES = (
        ('alumno', 'Alumnado'),
        ('profesor', 'Profesorado'),
        ('secretaria', 'Secretaría'),
        ('admin', 'Administrador'),
    )
    
    rol = models.CharField(max_length=15, choices=ROLES, default='alumno')
    puntos_acumulados = models.IntegerField(default=0) #

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"

class Tarea(models.Model):
    # Gestión de tareas creadas por secretaría para el alumnado.
    
    # Define la máquina de estados finita del ciclo de vida de una tarea
    ESTADOS = (
        ('solicitada', 'Solicitada'),
        ('en_proceso', 'En Proceso'),
        ('finalizada', 'Finalizada'),
        ('incompleta', 'Incompleta'),
        ('no_realizada', 'No Realizada'),
    )
    titulo = models.CharField(max_length=200) 
    descripcion = models.TextField() 
    puntos_otorgados = models.IntegerField() 
    estado = models.CharField(max_length=20, choices=ESTADOS, default='solicitada')
    
    # Relación con el alumno que realiza la tarea
    # Se usa SET_NULL para no borrar la tarea si se elimina el usuario
    # limit_choices_to impide asignar una tarea a un profesor o secretario
    alumno_asignado = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'rol': 'alumno'},
        related_name='tareas_asignadas'
    ) 

    def __str__(self):
        return f"{self.titulo} - {self.get_estado_display()}"

class NotaAcademica(models.Model):
    # Registro de las notas puestas por el profesorado y su conversión a puntos.
    alumno = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        limit_choices_to={'rol': 'alumno'},
        related_name='notas'
    )
    profesor = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True,
        limit_choices_to={'rol': 'profesor'}
    )
    asignatura = models.CharField(max_length=100) 
    valor_nota = models.DecimalField(max_digits=4, decimal_places=2, help_text="Nota sobre 10")
    puntos_generados = models.IntegerField(default=0, help_text="Puntos calculados automáticamente")

    def __str__(self):
        return f"{self.asignatura}: {self.valor_nota} ({self.alumno.username})"

class Recompensa(models.Model):
    # Catálogo de premios gestionado por secretaría
    titulo = models.CharField(max_length=150)
    coste_puntos = models.IntegerField()

    def __str__(self):
        return f"{self.titulo} - {self.coste_puntos} pts"

class CanjeoRecompensa(models.Model):
    # Historial transaccional para registrar qué alumno canjeó qué recompensa.
    
    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'alumno'})
    recompensa = models.ForeignKey(Recompensa, on_delete=models.SET_NULL, null=True)
    fecha_canjeo = models.DateTimeField(auto_now_add=True)
    # Se guarda el coste histórico (una snapshot) para evitar desajustes si el premio cambia de precio mañana
    puntos_gastados = models.IntegerField() # Guardamos el coste en el momento del canjeo por seguridad

    def __str__(self):
        return f"{self.alumno.username} canjeó {self.recompensa.titulo}"