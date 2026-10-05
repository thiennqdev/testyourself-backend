from app import create_app, db
from app.models import User  # đảm bảo bạn import đúng model User
from werkzeug.security import generate_password_hash

app = create_app()

def create_admin_user():
    existing_admin = User.query.filter_by(username="admin").first()
    if not existing_admin:
        admin = User(
            username="admin",
            name="System Administrator",
            email="admin@testyourself.local",
            password=generate_password_hash("admin123"),
            role="ADMIN"
        )
        db.session.add(admin)
        db.session.commit()
        print("[OK] Admin account created: username='admin', password='admin123', role='ADMIN'")
    else:
        print("[INFO] Admin account already exists.")

with app.app_context():
    db.create_all()
    create_admin_user()  # 👈 Thêm dòng này
    print("[OK] Database initialized.")
