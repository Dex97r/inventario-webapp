from datetime import datetime
from app.database import db
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model):
    """Modelo de base de datos para la gestión de usuarios locales de la WebApp."""
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Genera el hash para la contraseña proporcionada."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica la contraseña contra el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.correo}>"
