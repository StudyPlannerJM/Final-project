from app import create_app, db
from flask import render_template
from app.models import User, Task  # noqa: F401 - Importing the User model to ensure it's registered

app = create_app()

# This block ensures that the database is created when run.py is executed directly.
with app.app_context():
    db.drop_all() # Drops all tables (for development purposes)
    db.create_all() # Creates tables based on models.py

if __name__ == '__main__':
    app.run(debug=True)