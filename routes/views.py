from flask import Blueprint, render_template, redirect, session, url_for, request, jsonify
from db import get_db
from werkzeug.utils import secure_filename
import cloudinary.uploader

views_bp = Blueprint('views', __name__)

DEFAULT_LOGO = '/static/img/banner.svg'


def _config_value(clave, default=None):
    db = get_db()
    cur = db.connection.cursor()
    try:
        cur.execute("SELECT valor FROM configuracion WHERE clave = %s LIMIT 1", (clave,))
        row = cur.fetchone()
        return row[0] if row else default
    except Exception:
        return default
    finally:
        cur.close()


@views_bp.app_context_processor
def inject_site_config():
    db = get_db()
    cur = db.connection.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(total), 0) FROM visitas")
        row = cur.fetchone()
        visitas_totales = int(row[0] or 0)
    except Exception:
        visitas_totales = 0
    finally:
        cur.close()

    return {
        'visitas_totales': visitas_totales,
        'logo_url': _config_value('logo_url', DEFAULT_LOGO)
    }


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'telefono' not in session:
            return redirect(url_for('views.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'telefono' not in session:
            return redirect(url_for('views.login'))
        if session.get('rol') != 'admin':
            return redirect(url_for('views.index'))
        return f(*args, **kwargs)
    return decorated


@views_bp.route('/')
def index():
    # Una visita se registra cada vez que se carga la página principal.
    db = get_db()
    cur = db.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO visitas (fecha, total)
            VALUES (CURDATE(), 1)
            ON DUPLICATE KEY UPDATE total = total + 1
        """)
        db.connection.commit()
    finally:
        cur.close()

    return render_template('index.html')


@views_bp.route('/login')
def login():
    if 'telefono' in session:
        return redirect(url_for('views.index'))
    return render_template('auth.html')


@views_bp.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html')


@views_bp.route('/mensajes')
@login_required
def mensajes():
    return render_template('mensajes.html')


@views_bp.route('/notificaciones')
@login_required
def notificaciones():
    return render_template('notificaciones.html')


@views_bp.route('/buscar')
def buscar():
    return render_template('buscar.html')


@views_bp.route('/publicacion/<int:pub_id>')
def detalle_pub(pub_id):
    return render_template('detalle_pub.html', pub_id=pub_id)


@views_bp.route('/usuario/<telefono>')
def perfil_usuario(telefono):
    return render_template('perfil_usuario.html', telefono=telefono)


@views_bp.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')


@views_bp.route('/admin/logo', methods=['POST'])
@admin_required
def subir_logo():
    archivo = request.files.get('logo')

    if not archivo or not archivo.filename:
        return jsonify({'error': 'Selecciona una imagen.'}), 400

    extension = secure_filename(archivo.filename).rsplit('.', 1)[-1].lower() if '.' in archivo.filename else ''
    extensiones_permitidas = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

    if extension not in extensiones_permitidas:
        return jsonify({'error': 'Formato no permitido. Usa PNG, JPG, JPEG, GIF, WEBP o SVG.'}), 400

    try:
        resultado = cloudinary.uploader.upload(
            archivo,
            folder='comercio/configuracion',
            public_id='logo',
            overwrite=True,
            invalidate=True,
            resource_type='image'
        )
        logo_url = resultado['secure_url']

        db = get_db()
        cur = db.connection.cursor()
        cur.execute("""
            INSERT INTO configuracion (clave, valor)
            VALUES ('logo_url', %s)
            ON DUPLICATE KEY UPDATE valor = VALUES(valor)
        """, (logo_url,))
        db.connection.commit()
        cur.close()

        return jsonify({'ok': True, 'logo_url': logo_url})
    except Exception as e:
        return jsonify({'error': f'No se pudo subir el logo: {str(e)}'}), 500


@views_bp.route('/servicios')
def servicios():
    return render_template('servicios.html')


@views_bp.route('/emergencias')
def emergencias():
    return render_template('emergencias.html')
