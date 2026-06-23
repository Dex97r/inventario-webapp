# Sistema de Gestión de Activos Tecnológicos - WebApp

Esta es la aplicación web de interfaz corporativa para el **Sistema de Gestión de Activos Tecnológicos (SGAT)**. Está construida sobre **Flask** (Python 3.11) y **Bootstrap 5**, y funciona consumiendo una API externa de inventario para todas las operaciones sobre los equipos (CRUD y estadísticas). Cuenta con una base de datos propia para gestionar los usuarios locales del portal y proteger las rutas internas mediante sesiones seguras.

---

## Tecnologías Utilizadas

* **Python 3.11**
* **Flask** (Framework Web)
* **Flask-SQLAlchemy** (Gestión de base de datos ORM local para usuarios)
* **PostgreSQL** (Motor de base de datos)
* **Werkzeug Security** (Cifrado de contraseñas de usuarios)
* **requests** (Llamadas HTTP a la API externa de inventario)
* **python-dotenv** (Gestión de variables de entorno)
* **Bootstrap 5** (Diseño visual responsive y moderno)
* **Bootstrap Icons** (Iconografía del sistema)
* **Jinja2** (Motor de plantillas HTML)
* **Docker** (Contenedorización)
* **Gunicorn** (Servidor HTTP WSGI para producción)

---

## Variables de Entorno

La WebApp requiere configurar tres variables de entorno fundamentales para su correcto funcionamiento. Puede copiar el archivo `.env.example` para inicializar el suyo:

```bash
cp .env.example .env
```

| Variable | Descripción | Valor de Ejemplo |
| :--- | :--- | :--- |
| `DATABASE_URL` | URI de conexión a la base de datos PostgreSQL local para la WebApp | `postgresql://webapp_user:webapp_pass@db_webapp:5432/webapp_db` |
| `API_URL` | URL de la API FastAPI externa que gestiona el inventario de equipos | `http://api_service:8000` |
| `SECRET_KEY` | Clave secreta para encriptar las sesiones de Flask y evitar alteraciones | `ejemplo_clave_secreta_para_produccion_academica` |

---

## Credenciales de Prueba

Al levantar la aplicación por primera vez, el sistema autosembrará un usuario administrador por defecto si la tabla de usuarios se encuentra vacía:

* **Nombre de usuario:** `Administrador`
* **Correo electrónico:** `admin@demo.com`
* **Contraseña:** `admin123`

---

## Instalación y Ejecución

### Opción A: Ejecución Local (Desarrollo)

1. **Clonar e ingresar a la carpeta del proyecto:**
   ```bash
   cd inventario-webapp
   ```

2. **Crear e inicializar un entorno virtual (opcional pero recomendado):**
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/macOS:
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar el archivo `.env`:**
   Cree un archivo `.env` en la raíz del proyecto y configure sus variables. Si no define una `DATABASE_URL`, el sistema iniciará automáticamente con una base de datos SQLite en memoria (`sqlite:///:memory:`) para pruebas rápidas sin configurar PostgreSQL.

5. **Iniciar el servidor de desarrollo:**
   ```bash
   python -m app.main
   ```
   El portal estará accesible en: `http://localhost:5000`

---

### Opción B: Despliegue con Docker

La aplicación cuenta con un archivo `Dockerfile` configurado para producción académica utilizando **Gunicorn** escuchando en la interfaz `0.0.0.0` y el puerto `80`.

1. **Construir la imagen de Docker:**
   ```bash
   docker build -t inventario-webapp .
   ```

2. **Ejecutar el contenedor:**
   ```bash
   docker run -d -p 80:80 --name webapp-container \
     -e DATABASE_URL=postgresql://webapp_user:webapp_pass@db_webapp:5432/webapp_db \
     -e API_URL=http://api_service:8000 \
     -e SECRET_KEY=alguna_clave_secreta \
     inventario-webapp
   ```

---

## Flujo de Navegación del Sistema

1. **Página de Inicio (`/`)**:
   * Si no está autenticado, redirige automáticamente a la pantalla de **Login** (`/login`).
   * Si ya inició sesión, redirige al **Dashboard** (`/dashboard`).

2. **Registro de Usuarios (`/registro`)**:
   * Permite a los nuevos usuarios crear una cuenta local proporcionando su nombre, correo y contraseña.

3. **Iniciar Sesión (`/login`)**:
   * Pantalla de autenticación principal donde se validan las credenciales contra la base de datos local usando el hash cifrado de Werkzeug.

4. **Dashboard General (`/dashboard`)**:
   * Consume de manera asíncrona las estadísticas resumidas (`GET /equipos/estadisticas/resumen`) de la API de inventario.
   * Muestra métricas agrupadas en tarjetas interactivas: Total Equipos, Disponibles, Asignados, En Reparación y Retirados.

5. **Listado de Inventario (`/equipos`)**:
   * Muestra la tabla de equipos tecnológicos de forma responsiva.
   * Cuenta con un campo de búsqueda superior que filtra los equipos en memoria por código, nombre, marca o estado.

6. **Detalle del Equipo (`/equipos/<id>`)**:
   * Muestra la ficha técnica completa de un activo tecnológico consumiendo `GET /equipos/{id}`.

7. **Registrar Equipo (`/equipos/nuevo`)**:
   * Formulario con validaciones para registrar un equipo tecnológico en la API central mediante `POST /equipos`.

8. **Editar Equipo (`/equipos/editar/<id>`)**:
   * Carga los datos actuales del equipo e interactúa con `PUT /equipos/{id}` para actualizar cualquier campo operativo.

9. **Eliminar Equipo (`/equipos/eliminar/<id>`)**:
   * Ruta de seguridad interactiva que muestra una alerta de confirmación antes de impactar permanentemente el inventario enviando `DELETE /equipos/{id}` a la API.

---

## Tolerancia a Fallos (API Offline)

Si el servidor de la API central (`inventario-api`) no está disponible o presenta fallas de red:
* Las llamadas HTTP de `requests` lanzarán una excepción de conexión.
* El sistema captura esta excepción globalmente y muestra la vista `error.html` con un mensaje amigable al usuario indicando que el servicio de inventario se encuentra temporalmente fuera de línea.
* El sistema **no expone** excepciones internas de Flask, manteniendo la seguridad e integridad del software corporativo.
