"""Security settings applied by the app factory (headers, production cookies, proxy)."""

from werkzeug.middleware.proxy_fix import ProxyFix

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
}
HSTS = 'max-age=31536000; includeSubDomains'


def configure_production(app):
    """Settings that only make sense behind HTTPS on the hosting platform."""
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['BRAINDUMP_HSTS'] = True
    # Render's load balancer adds one X-Forwarded-For hop; trust exactly that one,
    # so request.remote_addr is the student's IP (used by the sign-in limiter).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)


def register_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if app.config.get('BRAINDUMP_HSTS'):
            response.headers.setdefault('Strict-Transport-Security', HSTS)
        return response
