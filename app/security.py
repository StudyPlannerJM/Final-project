"""Security settings applied by the app factory (headers, production cookies, proxy)."""

import os

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
    # Trust exactly as many X-Forwarded-For hops as there are proxies in front of
    # the app (1 for Render's load balancer), so request.remote_addr is the
    # student's address (used by the sign-in limiter). Too high lets clients
    # spoof it; too low makes everyone share the proxy's address.
    hops = int(os.environ.get('PROXY_FIX_X_FOR', '1'))
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=1)


def register_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if app.config.get('BRAINDUMP_HSTS'):
            response.headers.setdefault('Strict-Transport-Security', HSTS)
        return response
