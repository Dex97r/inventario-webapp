import os
from flask import Flask
from dotenv import load_dotenv
from app.database import db
from app.routes import main_bp
from app.seed import seed_db

# Cargar las variables de entorno desde el archivo .env si existe
load_dotenv()

def create_app():
    # Resolver rutas absolutas a carpetas de plantillas (templates) y archivos estáticos (static)
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Configuración de Flask a partir de variables de entorno
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_change_me_in_production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # URL base para consumir la API FastAPI de inventario
    app.config['API_URL'] = os.getenv('API_URL', 'http://localhost:8000')

    # Validar que la URL de base de datos esté presente
    if not app.config['SQLALCHEMY_DATABASE_URI']:
        # En caso de desarrollo local rápido, proveer un fallback a sqlite en memoria
        # (Esto ayuda a validar errores sintácticos localmente)
        app.logger.warning("DATABASE_URL no especificada en las variables de entorno. Usando SQLite en memoria como respaldo temporal.")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Inicializar Flask-SQLAlchemy con el ciclo de vida de la app
    db.init_app(app)

    # Registrar el Blueprint que contiene todas las rutas y handlers de error
    app.register_blueprint(main_bp)

    # Crear tablas y sembrar datos de prueba iniciales de forma segura
    with app.app_context():
        try:
            db.create_all()
            seed_db()
        except Exception as e:
            app.logger.error(f"Error crítico al inicializar la base de datos: {e}")

    return app

# Instancia de aplicación lista para Gunicorn o ejecución directa
app = create_app()

if __name__ == '__main__':
    # Para depuración local directa
    app.run(host='0.0.0.0', port=5000, debug=True)
