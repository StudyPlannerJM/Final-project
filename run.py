import os
from flask_migrate import Migrate  # type: ignore
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

app = create_app()
migrate = Migrate(app, db)

REQUIRED_TABLES = {
    "user",
    "task",
    "flashcard",
}


def should_seed_default_users():
    env_name = os.environ.get('FLASK_ENV', 'development').lower()
    if env_name == 'production':
        return (
            os.environ.get(
                'SEED_DEFAULT_USERS_PRODUCTION',
                'false'
            ).lower() == 'true'
        )
    return os.environ.get('SEED_DEFAULT_USERS', 'true').lower() == 'true'


def seed_default_users():
    with app.app_context():
        try:
            # Development-only bootstrap users by default.
            # Production bootstrapping is opt-in via env variable.
            admin = User.query.filter_by(email="admin@admin.com").first()
            if not admin:
                admin = User(
                    username="admin",  # type: ignore
                    email="admin@admin.com",  # type: ignore
                    password_hash=generate_password_hash(
                        "admin"
                    ),  # type: ignore
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
        except SQLAlchemyError as exc:
            db.session.rollback()
            print(
                "Warning: default user seeding skipped "
                f"due to DB error: {exc}"
            )


def seed_default_users_if_enabled():
    if not should_seed_default_users():
        return
    seed_default_users()


def get_missing_required_tables():
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
    return sorted(REQUIRED_TABLES - existing_tables)


@app.cli.command("seed-default-users")
def seed_default_users_command():
    """Seed default admin and student users."""
    seed_default_users()


@app.cli.command("verify-schema")
def verify_schema_command():
    """Fail if required tables are missing."""
    try:
        missing = get_missing_required_tables()
    except SQLAlchemyError as exc:
        raise SystemExit(
            "Schema verification failed due to DB error: "
            f"{exc}"
        ) from exc

    if missing:
        raise SystemExit(
            "Schema verification failed. Missing tables: "
            f"{', '.join(missing)}"
        )

    print("Schema verification passed.")


if __name__ == '__main__':
    try:
        seed_default_users_if_enabled()
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        print("\nServer stopped gracefully.")
