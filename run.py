from app import create_app, db
from flask import render_template
from app.models import User  # noqa: F401 - Importing the User model to ensure it's registered

app = create_app()

# This block ensures that the database is created when run.py is executed directly.
with app.app_context():
    db.create_all() # Creates tables based on models.py

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)