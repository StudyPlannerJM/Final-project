from app import create_app, db
from app.models import Task, User
from datetime import datetime

app = create_app()

with app.app_context():
    user = User.query.first()
    if user:
        tasks = Task.query.filter_by(user_id=user.id).filter(Task.due_date.isnot(None)).all()
        
        print(f"\n=== Tasks with Due Dates ===")
        for task in tasks:
            print(f"\nTask ID: {task.id}")
            print(f"Title: {task.title}")
            print(f"Due Date: {task.due_date}")
            print(f"ISO format: {task.due_date.isoformat()}")
            print(f"Date only: {task.due_date.date()}")
            print(f"Time: {task.due_date.time()}")
