from app import create_app

# Alternate WSGI entrypoint (some hosts look for `wsgi.py`).
# Exposes `app` variable for WSGI servers.
app = create_app()
