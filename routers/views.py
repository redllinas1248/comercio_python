from flask import Blueprint, render_template, redirect, session, url_for

views_bp = Blueprint('views', __name__)


@views_bp.route('/')
def index():
    """Feed principal — redirige a login si no hay sesión."""
    if 'telefono' not in session:
        return redirect(url_for('views.login'))
    return render_template('index.html')


@views_bp.route('/login')
def login():
    """Página de login/registro."""
    if 'telefono' in session:
        return redirect(url_for('views.index'))
    return render_template('auth.html')


@views_bp.route('/perfil')
def perfil():
    if 'telefono' not in session:
        return redirect(url_for('views.login'))
    return render_template('perfil.html')


@views_bp.route('/mensajes')
def mensajes():
    if 'telefono' not in session:
        return redirect(url_for('views.login'))
    return render_template('mensajes.html')


@views_bp.route('/notificaciones')
def notificaciones():
    if 'telefono' not in session:
        return redirect(url_for('views.login'))
    return render_template('notificaciones.html')
