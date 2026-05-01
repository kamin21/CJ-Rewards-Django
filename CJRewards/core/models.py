from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    # Modelo de usuario personalizado que extiende el de Django.
    # Almacena el rol y utiliza Firebase para los puntos.
    
    # Tupla que define los roles restrictivos del sistema (RBAC)
    ROLES = (
        ('alumno', 'Alumnado'),
        ('profesor', 'Profesorado'),
        ('secretaria', 'Secretaría'),
        ('admin', 'Administrador'),
    )
    
    rol = models.CharField(max_length=15, choices=ROLES, default='alumno')

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"