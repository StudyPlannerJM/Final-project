"""
Migration script to populate Category table from existing task categories
Run once after adding Category table
"""
from app import create_app, db
from app.models import User, Task, Category
from collections import defaultdict

def migrate_categories():
    """Create Category records from existing task category strings"""

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("CATEGORY MIGRATION SCRIPT")
        print("=" * 60)

        # Step 1: Find all unique categories per user
        print("\n[1/4] Analyzing existing categories...")

        category_map = {}  # (user_id, category_name) -> Category object

        for user in User.query.all():
            print(f"  Processing user: {user.username}")

            # Get all unique category strings for this user
            unique_categories = db.session.query(Task.category).filter(
                Task.user_id == user.id,
                Task.category.isnot(None),
                Task.category != ''
            ).distinct().all()

            print(f"    Found {len(unique_categories)} unique categories")

            # Create Category object for each unique string
            for (cat_name,) in unique_categories:
                # Check if category already exists
                existing = Category.query.filter_by(
                    user_id=user.id,
                    name=cat_name
                ).first()

                if not existing:
                    # Create new category
                    category = Category(
                        name=cat_name, # type: ignore
                        user_id=user.id, # type: ignore
                        is_default=False, # type: ignore
                        color=assign_color(cat_name) # type: ignore # Helper function
                    )
                    db.session.add(category)
                    db.session.flush()  # Get the ID without committing

                    category_map[(user.id, cat_name)] = category
                    print(f"      Created category: {cat_name}")
                else:
                    category_map[(user.id, cat_name)] = existing
                    print(f"      Category already exists: {cat_name}")

        # Commit all new categories
        db.session.commit()
        print(f"\n[2/4] Created {len(category_map)} category records")

        # Step 2: Update tasks to link to categories
        print("\n[3/4] Linking tasks to categories...")

        updated_count = 0
        for task in Task.query.all():
            if task.category and task.category.strip():
                key = (task.user_id, task.category)
                if key in category_map:
                    task.category_id = category_map[key].id
                    updated_count += 1

        db.session.commit()
        print(f"    Updated {updated_count} tasks with category_id")

        # Step 3: Verification
        print("\n[4/4] Verification...")
        total_categories = Category.query.count()
        tasks_with_category_id = Task.query.filter(Task.category_id.isnot(None)).count()
        tasks_with_category_string = Task.query.filter(
            Task.category.isnot(None),
            Task.category != ''
        ).count()

        print(f"    Total categories created: {total_categories}")
        print(f"    Tasks with category_id: {tasks_with_category_id}")
        print(f"    Tasks with category string: {tasks_with_category_string}")

        if tasks_with_category_id == tasks_with_category_string:
            print("\n✅ SUCCESS: All tasks migrated successfully!")
        else:
            print("\n⚠️  WARNING: Some tasks may not have been migrated")
            print(f"    Difference: {tasks_with_category_string - tasks_with_category_id}")

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)

def assign_color(category_name):
    """Assign colors based on category name"""
    color_map = {
        'homework': '#e74c3c',
        'project': '#3498db',
        'exam': '#e67e22',
        'reading': '#9b59b6',
        'personal': '#95a5a6',
        'work': '#16a085',
        'study': '#2ecc71',
    }

    # Check if category name contains any keyword
    for keyword, color in color_map.items():
        if keyword in category_name.lower():
            return color

    # Default color
    return '#3498db'

if __name__ == '__main__':
    migrate_categories()