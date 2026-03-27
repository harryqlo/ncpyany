import os
from flask import Flask, jsonify, request, send_file, g
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from config import (
    CORS_ALLOWED_ORIGINS,
    DB_PATH,
    DEBUG,
    FLASK_ENV,
    IS_PRODUCTION,
    JSON_SORT_KEYS,
    MAX_CONTENT_LENGTH,
    PERMANENT_SESSION_LIFETIME,
    SECRET_KEY,
    SESSION_REFRESH_EACH_REQUEST,
)
from app.security import (
    extract_bearer_token,
    get_user_from_token,
    init_security_schema,
    required_permission_for_request,
)

def create_app(config_overrides=None):
    """
    Crea y configura la aplicación Flask.
    """
    # BASE_DIR se define como el directorio que contiene la carpeta 'app'
    BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
    
    app = Flask(__name__, static_folder=os.path.join(BASE_DIR, '.'), static_url_path='')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    if IS_PRODUCTION and (not SECRET_KEY or SECRET_KEY == 'dev-secret-key-change-in-production'):
        raise RuntimeError('SECRET_KEY insegura para producción. Configura SECRET_KEY en variables de entorno.')

    app.config.update(
        SECRET_KEY=SECRET_KEY,
        DEBUG=DEBUG,
        ENV=FLASK_ENV,
        DATABASE=str(DB_PATH),
        JSON_SORT_KEYS=JSON_SORT_KEYS,
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
        PERMANENT_SESSION_LIFETIME=PERMANENT_SESSION_LIFETIME,
        SESSION_REFRESH_EACH_REQUEST=SESSION_REFRESH_EACH_REQUEST,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=IS_PRODUCTION,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    if config_overrides:
        app.config.update(config_overrides)

    allowed_origins = [origin.strip() for origin in CORS_ALLOWED_ORIGINS if origin.strip()]
    cors_origins = allowed_origins if allowed_origins else '*'
    CORS(app, resources={r'/api/*': {'origins': cors_origins}})

    init_security_schema()

    # Ruta principal para servir la página web
    @app.route('/')
    def index():
        """
        Sirve el archivo principal (página web)
        
        Método HTTP: GET
        Ruta: /
        
        Respuesta: HTML del dashboard
        """
        return send_file(os.path.join(BASE_DIR, 'index.html'))

    @app.route('/health')
    def healthcheck():
        """Healthcheck simple para validar despliegue en WSGI."""
        return jsonify({'ok': True, 'service': 'north_chrome', 'env': app.config.get('ENV', 'unknown')})

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Aquí es donde registraremos los Blueprints más adelante
    from .routes import (auth, dashboard, exports, settings, items, ingresos,
                         consumos, sellos, ordenes, componentes, empleados,
                         herramientas, auditorias, mantenimiento_profesional)
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(exports.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(items.bp)
    app.register_blueprint(ingresos.bp)
    app.register_blueprint(consumos.bp)
    app.register_blueprint(sellos.bp)
    app.register_blueprint(ordenes.bp)
    app.register_blueprint(componentes.bp)
    app.register_blueprint(empleados.bp)
    app.register_blueprint(herramientas.bp)
    app.register_blueprint(auditorias.bp)
    app.register_blueprint(mantenimiento_profesional.bp)

    @app.before_request
    def enforce_api_authentication():
        path = request.path or ''
        if not path.startswith('/api/'):
            return None

        permission_required = required_permission_for_request(path, request.method)

        public_paths = {
            '/api/auth/login',
            '/api/auth/bootstrap',
            '/api/auth/setup-status',
        }
        if path in public_paths:
            token = extract_bearer_token(request.headers.get('Authorization', ''))
            if token:
                user = get_user_from_token(token)
                if user:
                    g.current_user = user
            return None

        token = extract_bearer_token(request.headers.get('Authorization', ''))
        if not token:
            return jsonify({'ok': False, 'msg': 'No autenticado'}), 401

        user = get_user_from_token(token)
        if not user:
            return jsonify({'ok': False, 'msg': 'Token inválido o expirado'}), 401

        g.current_user = user
        user_permissions = set(user.get('permissions') or [])
        if permission_required and permission_required not in user_permissions and '*' not in user_permissions:
            return jsonify({'ok': False, 'msg': f'Permiso denegado: {permission_required}'}), 403

        return None

    return app
