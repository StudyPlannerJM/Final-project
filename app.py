from app import create_app

# Minimal WSGI/Flask entrypoint for hosting platforms (Vercel, Gunicorn, etc.)
# Vercel expects a top-level module exporting a variable named `app`.
app = create_app()
