import os
from flask_migrate import Migrate  # type: ignore
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()
migrate = Migrate(app, db)


def should_seed_default_users():
    env_name = os.environ.get('FLASK_ENV', 'development').lower()
    if env_name == 'production':
        return False
    return os.environ.get('SEED_DEFAULT_USERS', 'true').lower() == 'true'


with app.app_context():
    if should_seed_default_users():
        # Development-only bootstrap users.
        # Production should be seeded via migrations/admin flows.
        admin = User.query.filter_by(email="admin@admin.com").first()
        if not admin:
            admin = User(
                username="admin",  # type: ignore
                email="admin@admin.com",  # type: ignore
                password_hash=generate_password_hash("admin"),  # type: ignore
                is_admin=True  # type: ignore
            )
            db.session.add(admin)
            print("Admin created: admin@admin.com / admin")
        elif not admin.is_admin:
            admin.is_admin = True
            print("Admin user updated with admin privileges.")

        test_users = [
            {"username": "student1", "email": "student1@study.com"},
            {"username": "student2", "email": "student2@study.com"},
            {"username": "student3", "email": "student3@study.com"},
        ]
        for u_data in test_users:
            existing = User.query.filter_by(
                username=u_data["username"]
            ).first()
            if not existing:
                student = User(
                    username=u_data["username"],  # type: ignore
                    email=u_data["email"],  # type: ignore
                    is_admin=False  # type: ignore
                )
                student.set_password("user123")
                db.session.add(student)
                print(f"Test user created: {u_data['email']} / user123")
        db.session.commit()

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        print("\nServer stopped gracefully.")
