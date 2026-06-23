from app.database import db
from app.models import Usuario

def seed_db():
    """Siembra el usuario administrador de prueba en la base de datos si no existe."""
    try:
        admin_user = Usuario.query.filter_by(correo="admin@demo.com").first()
        if not admin_user:
            admin_user = Usuario(
                nombre="Administrador",
                correo="admin@demo.com"
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()
            print("Base de datos sembrada: Usuario de prueba creado (admin@demo.com / admin123)")
        else:
            print("El usuario de prueba admin@demo.com ya existe en la base de datos.")
    except Exception as e:
        db.session.rollback()
        print(f"Error al sembrar la base de datos: {e}")
        raise e
