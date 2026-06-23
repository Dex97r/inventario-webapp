from functools import wraps
import requests
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from app.database import db
from app.models import Usuario

# Definir el Blueprint para las rutas principales
main_bp = Blueprint('routes', __name__)

def login_required(f):
    """Decorador para proteger las rutas internas y requerir sesión activa."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta sección.', 'warning')
            return redirect(url_for('routes.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def api_request(method, endpoint, json=None, params=None):
    """Realiza peticiones HTTP a la API externa gestionando posibles caídas de servicio."""
    api_url = current_app.config.get('API_URL')
    url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        # Se establece un timeout prudencial de 5 segundos
        response = requests.request(method, url, json=json, params=params, timeout=5)
        return response
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error de conexión con la API en {url}: {e}")
        # Relanzamos la excepción para que sea capturada por el handler global
        raise e

def get_api_error_detail(response):
    """Extrae el mensaje de error legible retornado por FastAPI."""
    try:
        error_json = response.json()
        detail = error_json.get('detail')
        if isinstance(detail, list):
            # En caso de errores de validación de Pydantic, unir los detalles
            messages = []
            for item in detail:
                loc = ".".join([str(x) for x in item.get('loc', []) if x != 'body'])
                msg = item.get('msg', '')
                messages.append(f"Campo '{loc}': {msg}")
            return ", ".join(messages)
        elif isinstance(detail, str):
            return detail
        return f"Error del servidor (Código {response.status_code})"
    except Exception:
        return f"Error de comunicación (Código {response.status_code})"

@main_bp.app_errorhandler(requests.exceptions.RequestException)
def handle_api_connection_error(e):
    """Manejador global de Flask para capturar fallos de conexión con la API externa."""
    return render_template(
        'error.html', 
        title="Servicio Fuera de Línea", 
        message="El servicio de inventario se encuentra temporalmente fuera de línea. Por favor, intente de nuevo en unos minutos."
    ), 503

# --- RUTAS DE NAVEGACIÓN Y AUTENTICACIÓN ---

@main_bp.route('/')
def index():
    """Redirecciona a la página correspondiente según el estado de la sesión."""
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('routes.login'))

@main_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    """Registra un nuevo usuario local en la base de datos de la WebApp."""
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))
        
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        correo = request.form.get('correo', '').strip()
        password = request.form.get('password', '')

        if not nombre or not correo or not password:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('registro.html')

        # Verificar si el correo ya está registrado
        usuario_existente = Usuario.query.filter_by(correo=correo).first()
        if usuario_existente:
            flash('El correo electrónico ya está registrado.', 'danger')
            return render_template('registro.html')

        # Crear y persistir el usuario
        nuevo_usuario = Usuario(nombre=nombre, correo=correo)
        nuevo_usuario.set_password(password)
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('Registro exitoso. Ya puede iniciar sesión.', 'success')
            return redirect(url_for('routes.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al registrar usuario: {e}")
            flash('Ocurrió un error interno durante el registro. Intente de nuevo.', 'danger')
            
    return render_template('registro.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Autentica a un usuario y crea su sesión local."""
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))

    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        password = request.form.get('password', '')

        if not correo or not password:
            flash('Correo y contraseña son obligatorios.', 'danger')
            return render_template('login.html')

        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario and usuario.check_password(password):
            # Guardar información en la sesión de Flask
            session['user_id'] = usuario.id
            session['user_nombre'] = usuario.nombre
            session['user_correo'] = usuario.correo
            flash(f'¡Bienvenido de nuevo, {usuario.nombre}!', 'success')
            
            # Redirección amigable si el usuario venía de otra URL protegida
            next_page = request.args.get('next')
            return redirect(next_page or url_for('routes.dashboard'))
        else:
            flash('Credenciales incorrectas. Verifique su correo y contraseña.', 'danger')

    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    """Elimina la sesión del usuario."""
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('routes.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Muestra el resumen estadístico del inventario consumido desde la API."""
    response = api_request('GET', '/equipos/estadisticas/resumen')
    if response.status_code == 200:
        stats = response.json()
    else:
        stats = {
            "total": 0,
            "disponibles": 0,
            "asignados": 0,
            "en_reparacion": 0,
            "retirados": 0
        }
        flash('No se pudieron obtener las estadísticas en este momento.', 'warning')
        
    return render_template('dashboard.html', stats=stats)

# --- RUTAS DEL INVENTARIO DE EQUIPOS ---

@main_bp.route('/equipos')
@login_required
def equipos():
    """Muestra la lista de equipos con soporte para filtros de búsqueda en memoria."""
    # Obtenemos la lista de equipos de la API (obtenemos hasta 200 para filtrar localmente en memoria)
    response = api_request('GET', '/equipos', params={"limit": 200})
    
    if response.status_code == 200:
        lista_equipos = response.json()
    else:
        lista_equipos = []
        flash('No se pudo cargar la lista de equipos desde el inventario central.', 'danger')

    # Búsqueda en memoria
    query = request.args.get('q', '').strip()
    if query:
        query_lower = query.lower()
        lista_equipos = [
            eq for eq in lista_equipos
            if (query_lower in eq.get('codigo', '').lower() or
                query_lower in eq.get('nombre', '').lower() or
                query_lower in eq.get('marca', '').lower() or
                query_lower in eq.get('estado', '').lower())
        ]

    return render_template('equipos.html', equipos=lista_equipos, q=query)

@main_bp.route('/equipos/<int:id>')
@login_required
def equipo_detalle(id):
    """Muestra los detalles completos de un equipo tecnológico en particular."""
    response = api_request('GET', f'/equipos/{id}')
    if response.status_code == 200:
        equipo = response.json()
        return render_template('equipo_detalle.html', equipo=equipo)
    elif response.status_code == 404:
        flash('El equipo solicitado no existe.', 'warning')
    else:
        flash('Error al obtener la información del equipo.', 'danger')
        
    return redirect(url_for('routes.equipos'))

@main_bp.route('/equipos/nuevo', methods=['GET', 'POST'])
@login_required
def equipo_nuevo():
    """Registra un nuevo equipo tecnológico llamando a la API."""
    if request.method == 'POST':
        # Recolectar datos del formulario
        equipo_data = {
            "codigo": request.form.get('codigo', '').strip(),
            "nombre": request.form.get('nombre', '').strip(),
            "tipo": request.form.get('tipo', '').strip(),
            "marca": request.form.get('marca', '').strip(),
            "modelo": request.form.get('modelo', '').strip(),
            "numero_serie": request.form.get('numero_serie', '').strip(),
            "estado": request.form.get('estado', '').strip(),
            "ubicacion": request.form.get('ubicacion', '').strip()
        }

        # Validaciones básicas del lado del cliente/servidor Flask antes de enviar a la API
        if not all(equipo_data.values()):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('equipo_form.html', action='nuevo', equipo=equipo_data)

        # Enviar petición a la API
        response = api_request('POST', '/equipos', json=equipo_data)
        
        if response.status_code == 201:
            flash('Equipo registrado exitosamente en el inventario.', 'success')
            return redirect(url_for('routes.equipos'))
        else:
            error_msg = get_api_error_detail(response)
            flash(f"Error al registrar equipo: {error_msg}", 'danger')
            return render_template('equipo_form.html', action='nuevo', equipo=equipo_data)

    # Inicializar equipo vacío para la vista GET
    empty_equipo = {
        "codigo": "", "nombre": "", "tipo": "Laptop", "marca": "", 
        "modelo": "", "numero_serie": "", "estado": "Disponible", "ubicacion": ""
    }
    return render_template('equipo_form.html', action='nuevo', equipo=empty_equipo)

@main_bp.route('/equipos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def equipo_editar(id):
    """Edita los datos de un equipo tecnológico existente enviando los cambios a la API."""
    # Buscar el equipo existente
    response = api_request('GET', f'/equipos/{id}')
    if response.status_code != 200:
        if response.status_code == 404:
            flash('El equipo que intenta editar no existe.', 'warning')
        else:
            flash('Error al obtener los datos del equipo para edición.', 'danger')
        return redirect(url_for('routes.equipos'))

    equipo_existente = response.json()

    if request.method == 'POST':
        # Recolectar datos editados
        equipo_data = {
            "codigo": request.form.get('codigo', '').strip(),
            "nombre": request.form.get('nombre', '').strip(),
            "tipo": request.form.get('tipo', '').strip(),
            "marca": request.form.get('marca', '').strip(),
            "modelo": request.form.get('modelo', '').strip(),
            "numero_serie": request.form.get('numero_serie', '').strip(),
            "estado": request.form.get('estado', '').strip(),
            "ubicacion": request.form.get('ubicacion', '').strip()
        }

        if not all(equipo_data.values()):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('equipo_form.html', action='editar', equipo=equipo_data, id=id)

        # Enviar petición PUT a la API
        update_response = api_request('PUT', f'/equipos/{id}', json=equipo_data)
        
        if update_response.status_code == 200:
            flash('Equipo actualizado exitosamente.', 'success')
            return redirect(url_for('routes.equipo_detalle', id=id))
        else:
            error_msg = get_api_error_detail(update_response)
            flash(f"Error al actualizar equipo: {error_msg}", 'danger')
            return render_template('equipo_form.html', action='editar', equipo=equipo_data, id=id)

    return render_template('equipo_form.html', action='editar', equipo=equipo_existente, id=id)

@main_bp.route('/equipos/eliminar/<int:id>', methods=['GET', 'POST'])
@login_required
def equipo_eliminar(id):
    """Implementa la pantalla de confirmación y posterior eliminación del equipo."""
    # Obtener el equipo a eliminar
    response = api_request('GET', f'/equipos/{id}')
    if response.status_code != 200:
        if response.status_code == 404:
            flash('El equipo que intenta eliminar no existe.', 'warning')
        else:
            flash('Error al obtener la información del equipo.', 'danger')
        return redirect(url_for('routes.equipos'))

    equipo = response.json()

    if request.method == 'POST':
        # Proceder con la eliminación en la API
        delete_response = api_request('DELETE', f'/equipos/{id}')
        if delete_response.status_code == 200:
            flash('Equipo eliminado exitosamente del inventario.', 'success')
        else:
            error_msg = get_api_error_detail(delete_response)
            flash(f"Error al eliminar equipo: {error_msg}", 'danger')
        return redirect(url_for('routes.equipos'))

    return render_template('confirmar_eliminacion.html', equipo=equipo)
