from app import create_app, db
from app.models import Task, Category

app = create_app()

with app.app_context():
    print("=" * 60)
    print("CHECKING TASK CATEGORIES")
    print("=" * 60)
    
    # Check all tasks
    tasks = Task.query.all()
    print(f"\nTotal tasks: {len(tasks)}")
    
    for task in tasks[:5]:  # Show first 5
        print(f"\nTask: {task.title}")
        print(f"  - category_id: {task.category_id}")
        print(f"  - task_category: {task.task_category}")
        if task.task_category:
            print(f"  - Category name: {task.task_category.name}")
            print(f"  - Category color: {task.task_category.color}")
            print(f"  - Category icon: {task.task_category.icon}")
        else:
            print(f"  - ❌ NO CATEGORY ASSIGNED!")
    
    # Check categories
    print("\n" + "=" * 60)
    print("ALL CATEGORIES")
    print("=" * 60)
    categories = Category.query.all()
    for cat in categories:
        print(f"Category: {cat.name} (color: {cat.color}, user_id: {cat.user_id})")
