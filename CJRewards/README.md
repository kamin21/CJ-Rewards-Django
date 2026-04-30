# CJ-Rewards 🏆

Sistema de gamificación escolar construido con Django y Firebase. Los alumnos ganan puntos completando tareas y obteniendo buenas calificaciones, para luego canjearlos por premios en una tienda virtual. Gestionado por profesores y secretaría.

## Requisitos Previos
- **Python 3.10+**
- **Git**
- Una cuenta de **Firebase** con un proyecto de Firestore activo.

---

## Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd CJRewards
```

### 2. Crear y Activar un Entorno Virtual
```bash
python -m venv venv
```
- **Windows:** `venv\Scripts\activate`
- **macOS / Linux:** `source venv/bin/activate`

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar las Variables de Entorno
Crea un archivo **`.env.local`** en la raíz del proyecto (a la misma altura que `manage.py`) con el siguiente contenido:
```env
SECRET_KEY=tu-clave-secreta-de-django
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```
> Para generar una `SECRET_KEY` segura, ejecuta en la terminal:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

### 5. Configurar Firebase
1. Ve a la [Consola de Firebase](https://console.firebase.google.com/) y entra en tu proyecto.
2. Ve a **Configuración del proyecto > Cuentas de servicio > Generar nueva clave privada**.
3. Descarga el archivo JSON y colócalo en la carpeta `Firebase_conf/` con el nombre:
   ```
   Firebase_conf/CJ_Rewards_Credentials.json
   ```

### 6. Preparar la Base de Datos
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Crear un Superusuario (Admin)
```bash
python manage.py createsuperuser
```
Sigue los pasos de la terminal. **Importante:** al crear el superusuario, entra después al panel de Django Admin (`/admin`) y asígnale el rol `admin` en la sección "Información de Gamificación" para que pueda acceder al Panel de Control Maestro.

### 8. Levantar el Servidor
```bash
python manage.py runserver
```
Accede a **http://127.0.0.1:8000/** desde tu navegador.

---

## Despliegue en Vercel

El proyecto está preparado para desplegarse en Vercel **sin necesidad de enlazar el repositorio de GitHub**.

### 1. Instalar Vercel CLI
```bash
npm i -g vercel
```

### 2. Configurar Variables de Entorno en Vercel
Desde el dashboard de Vercel (Settings > Environment Variables), añade:
| Variable | Valor |
|---|---|
| `SECRET_KEY` | Tu clave secreta de Django |
| `DEBUG` | `False` |
| `FIREBASE_CREDENTIALS_JSON` | El contenido completo del archivo JSON de Firebase (pegar todo el texto) |

### 3. Desplegar
```bash
vercel --prod
```

> **Nota:** La base de datos SQLite en Vercel es de **solo lectura**. Para crear o modificar usuarios, hazlo en tu entorno local y vuelve a desplegar con `vercel --prod`.

---

## Estructura de Roles

| Rol | Funcionalidades |
|---|---|
| **Admin** | Panel de Control Maestro con métricas globales y registro de logs de acceso (almacenados en Firebase). |
| **Secretaría** | Publicación de tareas, gestión de premios en la tienda, validación de méritos y auditoría de canjes. |
| **Profesor** | Asignación de notas académicas que generan puntos de forma automática según las reglas de negocio. |
| **Alumno** | Tablón de misiones, tienda de premios, monedero virtual e historial de puntos ganados y gastados. |

---

## Tecnologías Utilizadas

- **Backend:** Django 6.0
- **Base de Datos Local:** SQLite (usuarios y autenticación)
- **Base de Datos en la Nube:** Firebase Cloud Firestore (tareas, premios, puntos, logs)
- **Frontend:** Tailwind CSS (CDN), HTML5
- **Seguridad:** django-axes (entorno local), sistema de logs propio en Firebase (producción)
- **Despliegue:** Vercel (Serverless)
