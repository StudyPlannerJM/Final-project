from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

# This block ensures that the database is created when run.py is executed directly.
with app.app_context():
    db.drop_all()  # Drops all tables (for development purposes)
    db.create_all()  # Creates tables based on models.py
    # SIMPLE default admin creator
    admin = User.query.filter_by(email="admin@admin.com").first()
    if not admin:
        admin = User(
            username="admin",   #type: ignore
            email="admin@admin.com",    #type: ignore
            password_hash=generate_password_hash("admin")   #type: ignore
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin created: admin@admin.com / admin")
if __name__ == '__main__':
    app.run(debug=True)