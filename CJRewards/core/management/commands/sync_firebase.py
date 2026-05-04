"""
sync_firebase.py — Comando de gestión para sincronizar usuarios Django ↔ Firebase.
"""
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Usuario
from core.gestor_firebase import GestorCJRewards

class Command(BaseCommand):
    help = 'Sincroniza los usuarios entre Django (SQLite) y Firebase Firestore.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Aplica las correcciones detectadas.')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        ruta_json = os.path.join(settings.BASE_DIR, 'Firebase_conf', 'CJ_Rewards_Credentials.json')
        db_manager = GestorCJRewards(ruta_credenciales=ruta_json)

        django_users = {u.username: u for u in Usuario.objects.all()}
        firebase_users = {doc.id: doc.to_dict() for doc in db_manager.db.collection('usuarios').stream()}

        # 1. Django -> Firebase
        missing_in_firebase = set(django_users.keys()) - set(firebase_users.keys())
        for username in missing_in_firebase:
            user = django_users[username]
            self.stdout.write(self.style.WARNING(f'Usuario {username} falta en Firebase.'))
            if apply_changes:
                db_manager.crear_usuario(username, user.email, user.rol)
                self.stdout.write(self.style.SUCCESS(f'  Creado en Firebase.'))

        # 2. Sync desincronizados
        common = set(django_users.keys()) & set(firebase_users.keys())
        for username in common:
            dj = django_users[username]
            fb = firebase_users[username]
            if dj.rol != fb.get('rol') or dj.email != fb.get('email'):
                self.stdout.write(self.style.WARNING(f'Usuario {username} desincronizado.'))
                if apply_changes:
                    db_manager.db.collection('usuarios').document(username).set({
                        'email': dj.email,
                        'rol': dj.rol
                    }, merge=True)
                    self.stdout.write(self.style.SUCCESS(f'  Actualizado.'))

        self.stdout.write(self.style.SUCCESS('Sincronización finalizada.'))
