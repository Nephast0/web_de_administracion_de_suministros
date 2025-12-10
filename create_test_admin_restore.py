from app import create_app, db
from app.models import Usuario

app = create_app()

with app.app_context():
    # Check if admin exists
    admin = Usuario.query.filter_by(usuario='admin').first()
    if admin:
        print("Updating existing admin user...")
        admin.nombre = 'Administrador Test'
        admin.direccion = 'Calle Principal 123'
        admin.rol = 'admin'
        # Explicitly set password hash if needed, or use method
        admin.hash_contrasenya('admin123') 
    else:
        print("Creating new admin user...")
        admin = Usuario(
            nombre='Administrador Test',
            usuario='admin',
            direccion='Calle Principal 123',
            contrasenya='admin123',
            rol='admin'
        )
        db.session.add(admin)
    
    db.session.commit()
    print("Admin user 'admin' with password 'admin123' is ready.")
