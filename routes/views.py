from flask import Blueprint, render_template, redirect, session, url_for

views_bp = Blueprint('views', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'telefono' not in session:
            return redirect(url_for('views.login'))
        return f(*args, **kwargs)
    return decorated


@views_bp.route('/')
@login_required
def index():
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
@login_required
def buscar():
    return render_template('buscar.html')

@views_bp.route('/publicacion/<int:pub_id>')
@login_required
def detalle_pub(pub_id):
    return render_template('detalle_pub.html', pub_id=pub_id)

@views_bp.route('/usuario/<telefono>')
@login_required
def perfil_usuario(telefono):
    return render_template('perfil_usuario.html', telefono=telefono)

@views_bp.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@views_bp.route('/servicios')
@login_required
def servicios():
    return render_template('servicios.html')

@views_bp.route('/emergencias')
@login_required
def emergencias():
    return render_template('emergencias.html')
