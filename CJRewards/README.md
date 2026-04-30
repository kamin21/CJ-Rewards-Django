# CJ-Rewards

Sistema de gestión de recompensas escolares basado en Django con integración a Firebase. Permite a los alumnos ganar puntos realizando tareas o mediante calificaciones, para luego canjearlos en una tienda de premios. Todo administrado por profesores y secretaría.

## Requisitos Previos
- **Python 3.8+**
- **Git**
- **Node.js** (Opcional, en caso de necesitar recompilar estilos con Tailwind u otras dependencias listadas en `package.json`).

---

## Instalación y Configuración

Sigue estos pasos para instalar y preparar el proyecto en un nuevo dispositivo.

### 1. Clonar el repositorio
Abre una terminal y clona el repositorio desde GitHub:
```bash
git clone <URL_DE_TU_REPOSITORIO_EN_GITHUB>
cd "CJ-Rewards Django/CJRewards" # Ajusta el nombre de la carpeta según corresponda
```

### 2. Crear y Activar un Entorno Virtual
Para no causar conflictos con otros proyectos, crea un entorno virtual de Python:
```bash
python -m venv venv
```
Activa el entorno virtual:
- **Windows:** `venv\Scripts\activate`
- **macOS / Linux:** `source venv/bin/activate`

### 3. Instalar Dependencias
Instala todas las librerías necesarias de Python utilizando el archivo `requirements.txt`:
```bash
pip install -r requirements.txt
```
*(Si necesitas las dependencias de Node.js, ejecuta también `npm install`)*.

### 4. Variables de Entorno y Firebase
El proyecto utiliza variables de entorno y conexión a Firebase para funcionar correctamente:
1. Asegúrate de tener un archivo **`.env`** o **`.env.local`** en la raíz del proyecto (a la misma altura que `manage.py`). Debe contener las credenciales de tu proyecto (como `SECRET_KEY`, parámetros de Base de Datos si no usas SQLite, etc.).
2. **Firebase:** Asegúrate de colocar el archivo JSON con las credenciales de servicio de tu proyecto de Firebase dentro de la carpeta `Firebase_conf/`, con el nombre correcto configurado en tu `settings.py`.

### 5. Preparar la Base de Datos
Ejecuta las migraciones para generar las tablas correspondientes en la base de datos (por defecto SQLite `db.sqlite3`):
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Crear un Usuario Administrador
Para poder acceder a las herramientas globales y al panel general (`/admin`), crea un superusuario:
```bash
python manage.py createsuperuser
```
Sigue los pasos que te pedirá la terminal (Nombre de usuario, correo electrónico y contraseña).

### 7. Levantar el Servidor
Finalmente, inicia el servidor de desarrollo local:
```bash
python manage.py runserver
```
Accede a **http://127.0.0.1:8000/** desde tu navegador web. ¡El sistema de CJ-Rewards estará listo para utilizarse!

---

## Estructura de Roles

El proyecto cuenta con vistas y flujos distintos de acuerdo al tipo de usuario:
- **Admin:** Panel maestro para revisar las métricas totales y forzar sincronización con Firebase.
- **Secretaría:** Gestión del inventario de premios, validación de tareas de los alumnos y auditorías de canjes.
- **Profesor:** Panel simplificado para asignar notas, lo cual genera recompensas de puntos automáticas al alumnado.
- **Alumno:** Vista de tienda, tablón de actividades, y el registro de todos sus puntos ganados y gastados.
