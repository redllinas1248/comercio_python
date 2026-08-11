from flask import Flask, request, jsonify
from security import validate_csrf
from config import Config, init_cloudinary
from db import init_db

app = Flask(__name__)
app.config.from_object(Config)

# En producción los secretos deben existir como variables de entorno.
_REQUIRED_SECRETS = (
    'SECRET_KEY',
    'MYSQL_HOST',
    'MYSQL_USER',
    'MYSQL_PASSWORD',
    'MYSQL_DB',
    'CLOUDINARY_CLOUD_NAME',
    'CLOUDINARY_API_KEY',
    'CLOUDINARY_API_SECRET',
)
_missing = [name for name in _REQUIRED_SECRETS if not app.config.get(name)]
if _missing:
    raise RuntimeError('Faltan variables de entorno obligatorias: ' + ', '.join(_missing))


@app.before_request
def protect_api_with_csrf():
    if not request.path.startswith('/api/'):
        return None
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    # Todas las operaciones que cambian estado deben llevar token CSRF.
    if not validate_csrf():
        return jsonify({'error': 'Token CSRF inválido o ausente'}), 403
    return None


@app.after_request
def security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    if request.is_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response

init_db(app)
init_cloudinary(app)

from routes.auth import auth_bp
from routes.publicaciones import pub_bp
from routes.comentarios import com_bp
from routes.likes import likes_bp
from routes.mensajes import msg_bp
from routes.notificaciones import notif_bp
from routes.directorio import dir_bp
from routes.views import views_bp

app.register_blueprint(auth_bp)
app.register_blueprint(pub_bp)
app.register_blueprint(com_bp)
app.register_blueprint(likes_bp)
app.register_blueprint(msg_bp)
app.register_blueprint(notif_bp)
app.register_blueprint(dir_bp)
app.register_blueprint(views_bp)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
