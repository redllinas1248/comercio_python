import os
import logging
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from security import validate_csrf
from config import Config, init_cloudinary
from db import init_db
from routes.publicaciones import limpiar_publicaciones_antiguas

app = Flask(__name__)
app.config.from_object(Config)

# Configurar logging
if not app.debug:
    app.logger.setLevel(logging.ERROR)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
    app.logger.addHandler(handler)

# Manejador de errores global
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Error no controlado: {e}", exc_info=True)
    return jsonify({'error': 'Error interno del servidor'}), 500

# Verificar variables de entorno obligatorias
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
    if not validate_csrf():
        return jsonify({'error': 'Token CSRF inválido o ausente'}), 403
    return None


@app.after_request
def security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' data: https://res.cloudinary.com; "
        "media-src 'self' https://res.cloudinary.com; "
        "script-src 'self' 'unsafe-inline' https://www.youtube.com; "
        "frame-src https://www.youtube.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self';"
    )
    if request.is_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response

init_db(app)
init_cloudinary(app)

# ===== REGISTRAR BLUEPRINTS =====
from routes.auth import auth_bp
from routes.publicaciones import pub_bp
from routes.comentarios import com_bp
from routes.likes import likes_bp
from routes.mensajes import msg_bp
from routes.notificaciones import notif_bp
from routes.directorio import dir_bp
from routes.views import views_bp
from routes.transmisiones import transmisiones_bp

app.register_blueprint(auth_bp)
app.register_blueprint(pub_bp)
app.register_blueprint(com_bp)
app.register_blueprint(likes_bp)
app.register_blueprint(msg_bp)
app.register_blueprint(notif_bp)
app.register_blueprint(dir_bp)
app.register_blueprint(views_bp)
app.register_blueprint(transmisiones_bp)


# ===== RUTA PÚBLICA DE TRANSMISIONES =====
@views_bp.route('/transmisiones')
def transmisiones():
    return render_template('transmisiones.html')


# ===== SCHEDULER: LIMPIEZA AUTOMÁTICA =====
def limpieza_programada():
    with app.app_context():
        try:
            eliminadas = limpiar_publicaciones_antiguas()
            app.logger.info(f"Limpieza programada: {eliminadas} publicaciones eliminadas")
        except Exception as e:
            app.logger.error(f"Error en limpieza programada: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(
    limpieza_programada,
    'cron',
    hour=3,
    minute=0,
    id='limpieza_publicaciones',
    replace_existing=True
)
scheduler.start()

import atexit
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)