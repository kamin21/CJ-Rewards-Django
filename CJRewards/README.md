# CJ-Rewards 🏆

Sistema de gamificación escolar construido con **Django + Firebase**. El alumnado acumula puntos completando tareas y obteniendo buenas calificaciones, y los canjea por premios en una tienda virtual. El profesorado y la secretaría gestionan la plataforma desde paneles dedicados.

---

## Arquitectura

El proyecto sigue una **arquitectura híbrida de doble base de datos**:

| Capa | Tecnología | Qué almacena |
|---|---|---|
| **Autenticación y Roles** | Django + SQLite/PostgreSQL | Usuarios, contraseñas (hasheadas), roles (RBAC) |
| **Economía y Gamificación** | Firebase Cloud Firestore | Tareas, premios, puntos, historial de notas, canjes |
| **Logs de Seguridad** | Firebase Cloud Firestore | Intentos de login (éxitos y fallos), IPs |

**Flujo de una petición:** `Navegador → Django (View) → GestorCJRewards → Firestore → Template HTML`

---

## Roles del Sistema (RBAC)

| Rol | Capacidades |
|---|---|
| **Alumno** | Ver su saldo, aceptar tareas, canjear premios, ver su historial cronológico |
| **Profesor** | Registrar notas académicas que generan puntos automáticamente |
| **Secretaría** | Crear/validar tareas, gestionar el catálogo de premios, auditar canjes |
| **Admin** | Crear/eliminar usuarios, ver logs de acceso y métricas del sistema |

---

## Requisitos Previos

- **Python 3.10+**
- **Node.js / npm** (solo para compilar Tailwind CSS en local)
- Una cuenta de **Firebase** con un proyecto de **Cloud Firestore** activo

---

## Instalación Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/kamin21/CJ-Rewards-Django.git
cd CJRewards
```

### 2. Crear y activar entorno virtual
```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

### 3. Instalar dependencias Python
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crea el archivo **`.env.local`** en la raíz del proyecto (junto a `manage.py`):
```env
SECRET_KEY=tu-clave-secreta-de-django
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```
> Para generar una `SECRET_KEY` segura:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

### 5. Configurar credenciales de Firebase
1. Accede a la [Consola de Firebase](https://console.firebase.google.com/) → tu proyecto.
2. Ve a **Configuración del proyecto → Cuentas de servicio → Generar nueva clave privada**.
3. Descarga el archivo JSON y colócalo en:
   ```
   Firebase_conf/CJ_Rewards_Credentials.json
   ```
> ⚠️ Este archivo está en `.gitignore`. **Nunca lo subas a un repositorio público.**

### 6. Aplicar migraciones
```bash
python manage.py migrate
```

### 7. Crear el primer usuario administrador
```bash
python manage.py createsuperuser
```
Tras crearlo, accede a `/admin/` y asígnale el **rol `admin`** en la sección "Información de Rol" para que pueda acceder al Panel de Control Maestro.

### 8. Levantar el servidor de desarrollo
```bash
python manage.py runserver
```
Accede a **http://127.0.0.1:8000/**

---

## Despliegue en Vercel (Producción Serverless)

El proyecto está preparado para Vercel. El sistema de archivos de Vercel es de **solo lectura**, por lo que se han realizado adaptaciones específicas:
- Las **sesiones** usan cookies firmadas (`signed_cookies`) en lugar de SQLite.
- El sistema de bloqueo de fuerza bruta es propio (Firebase), sin `django-axes`.
- Las **credenciales de Firebase** se inyectan como variable de entorno.

### Variables de entorno en Vercel
En el panel de Vercel → **Settings → Environment Variables**, añade:

| Variable | Valor |
|---|---|
| `SECRET_KEY` | Tu clave secreta de Django |
| `DEBUG` | `False` |
| `FIREBASE_CREDENTIALS` | El contenido **completo** del JSON de Firebase (todo en una línea) |

### Desplegar
```bash
npm i -g vercel   # Solo la primera vez
vercel --prod
```

---

## Estructura del Proyecto

```
CJRewards/
├── CJRewards/
│   ├── settings.py       # Configuración Django (env vars, seguridad, Axes)
│   └── urls.py           # Enrutador raíz (incluye core.urls, rutas de secretaría)
├── core/
│   ├── decorators.py     # RBAC: @rol_requerido para control de acceso
│   ├── gestor_firebase.py # Capa de datos: toda la lógica con Firestore
│   ├── models.py         # Solo modelo Usuario (puntos viven en Firebase)
│   ├── urls.py           # Rutas de la app (dashboards por rol)
│   ├── views.py          # Controladores HTTP
│   └── templates/        # HTML por rol (dashboards/alumno/, /profesor/, etc.)
├── Firebase_conf/
│   └── CJ_Rewards_Credentials.json  # ← NO subir a Git
├── .env.local            # Variables de entorno locales ← NO subir a Git
├── requirements.txt
└── vercel.json
```

---

## Seguridad

- **Contraseñas:** hasheadas con el sistema nativo de Django (`set_password`).
- **RBAC:** El decorador `@rol_requerido` previene escalada de privilegios (IDOR).
- **Rate Limiting:** La función `comprobar_rate_limit` en `gestor_firebase.py` bloquea IPs con más de 5 fallos en 10 minutos, consultando los logs de Firebase.
- **Transacciones atómicas:** Las operaciones de puntos usan `@firestore.transactional` para evitar condiciones de carrera.
- **Producción:** HTTPS obligatorio, cookies seguras y HSTS de 1 año.

---

## Tecnologías

- **Backend:** Django 6.0 · Python 3.10+
- **Base de datos relacional:** SQLite (local) · PostgreSQL (producción)
- **Base de datos en la nube:** Firebase Cloud Firestore
- **Frontend:** Tailwind CSS (CDN) · HTML5
- **Despliegue:** Vercel (Serverless)
