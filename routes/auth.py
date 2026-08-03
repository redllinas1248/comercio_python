from flask import Blueprint, request, jsonify, session
from db import get_db
import bcrypt

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/registro', methods=['POST'])
def registro():
    """Registrar nuevo usuario con teléfono y PIN."""
    data = request.get_json()
    telefono = data.get('telefono', '').strip()
    pin      = data.get('pin', '').strip()
    usuario  = data.get('usuario', '').strip() or telefono
    nombre   = data.get('nombre', '').strip()

    if not telefono or not pin:
        return jsonify({'error': 'Teléfono y PIN son obligatorios'}), 400
    if len(pin) != 4 or not pin.isdigit():
        return jsonify({'error': 'El PIN debe ser de 4 dígitos'}), 400

    db = get_db()
    cur = db.connection.cursor()

    # Verificar si el teléfono ya existe
    cur.execute("SELECT id FROM usuarios WHERE telefono = %s", (telefono,))
    if cur.fetchone():
        return jsonify({'error': 'Este teléfono ya está registrado'}), 409

    # Encriptar PIN con bcrypt
    pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()

    localidad = data.get('localidad', '').strip() or None

    cur.execute(
        "INSERT INTO usuarios (telefono, usuario, nombre, pin, localidad) VALUES (%s, %s, %s, %s, %s)",
        (telefono, usuario, nombre or None, pin_hash, localidad)
    )
    db.connection.commit()
    nuevo_id = cur.lastrowid
    cur.close()

    session['telefono'] = telefono
    session['usuario_id'] = nuevo_id
    return jsonify({'mensaje': 'Registro exitoso', 'id': nuevo_id}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Iniciar sesión con teléfono y PIN."""
    data = request.get_json()
    telefono = data.get('telefono', '').strip()
    pin      = data.get('pin', '').strip()

    if not telefono or not pin:
        return jsonify({'error': 'Teléfono y PIN son obligatorios'}), 400

    db = get_db()
    cur = db.connection.cursor()
    cur.execute(
        "SELECT id, pin, nombre, foto, rol FROM usuarios WHERE telefono = %s",
        (telefono,)
    )
    usuario = cur.fetchone()
    cur.close()

    if not usuario:
        return jsonify({'error': 'Teléfono no registrado'}), 404

    _id, pin_hash, nombre, foto, rol = usuario

    if not bcrypt.checkpw(pin.encode(), pin_hash.encode()):
        return jsonify({'error': 'PIN incorrecto'}), 401

    session['telefono']   = telefono
    session['usuario_id'] = _id
    session['rol']        = rol

    return jsonify({
        'mensaje': 'Login exitoso',
        'usuario': {'id': _id, 'nombre': nombre, 'foto': foto, 'rol': rol}
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'mensaje': 'Sesión cerrada'})


@auth_bp.route('/perfil', methods=['PUT'])
def actualizar_perfil():
    """Actualizar nombre, apellido, localidad, correo, tipo."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    data      = request.get_json()
    telefono  = session['telefono']
    campos    = ['nombre', 'apellido', 'localidad', 'correo', 'tipo',
                 'mostrar_telefono', 'mostrar_correo']
    updates   = {k: data[k] for k in campos if k in data}

    if not updates:
        return jsonify({'error': 'Nada que actualizar'}), 400

    set_clause = ', '.join(f"{k} = %s" for k in updates)
    valores    = list(updates.values()) + [telefono]

    db = get_db()
    cur = db.connection.cursor()
    cur.execute(f"UPDATE usuarios SET {set_clause} WHERE telefono = %s", valores)
    db.connection.commit()
    cur.close()

    return jsonify({'mensaje': 'Perfil actualizado'})


@auth_bp.route('/yo', methods=['GET'])
def yo():
    """Devuelve datos del usuario en sesión."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    db = get_db()
    cur = db.connection.cursor()
    cur.execute(
        """SELECT id, telefono, usuario, nombre, apellido, localidad,
                  foto, rol, correo, tipo, mostrar_telefono, mostrar_correo
           FROM usuarios WHERE telefono = %s""",
        (session['telefono'],)
    )
    row = cur.fetchone()
    cur.close()

    if not row:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    keys = ['id','telefono','usuario','nombre','apellido','localidad',
            'foto','rol','correo','tipo','mostrar_telefono','mostrar_correo']
    return jsonify(dict(zip(keys, row)))


@auth_bp.route('/foto', methods=['POST'])
def subir_foto():
    """Subir o cambiar foto de perfil."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    if 'foto' not in request.files:
        return jsonify({'error': 'No se envió ninguna imagen'}), 400

    import os, time
    from werkzeug.utils import secure_filename

    foto = request.files['foto']
    ext  = foto.filename.rsplit('.', 1)[-1].lower()
    if ext not in {'png','jpg','jpeg','gif','webp'}:
        return jsonify({'error': 'Formato no permitido'}), 400

    nombre_archivo = f"perfil_{session['telefono']}_{int(time.time())}.{ext}"
    carpeta = os.path.join('static', 'img', 'perfiles')
    os.makedirs(carpeta, exist_ok=True)
    foto.save(os.path.join(carpeta, nombre_archivo))

    ruta = f"img/perfiles/{nombre_archivo}"
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("UPDATE usuarios SET foto = %s WHERE telefono = %s",
                (ruta, session['telefono']))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Foto actualizada', 'ruta': ruta})


@auth_bp.route('/usuario/<telefono>', methods=['GET'])
def perfil_publico(telefono):
    """Perfil público de cualquier usuario."""
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT id, telefono, nombre, apellido, localidad, foto, tipo
        FROM usuarios WHERE telefono = %s
    """, (telefono,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({'error': 'Usuario no encontrado'}), 404
    keys = ['id','telefono','nombre','apellido','localidad','foto','tipo']
    u = dict(zip(keys, row))
    # Conteo de publicaciones
    cur.execute("SELECT COUNT(*) FROM publicaciones WHERE telefono = %s", (telefono,))
    u['total_pubs'] = cur.fetchone()[0]
    cur.close()
    return jsonify(u)


@auth_bp.route('/admin/usuarios', methods=['GET'])
def admin_usuarios():
    """Lista todos los usuarios para el panel admin."""
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT id, telefono, nombre, localidad, rol, foto,
               (SELECT COUNT(*) FROM publicaciones p WHERE p.telefono = u.telefono) AS total_pubs
        FROM usuarios u ORDER BY id DESC
    """)
    rows = cur.fetchall()
    keys = ['id','telefono','nombre','localidad','rol','foto','total_pubs']
    cur.close()
    return jsonify([dict(zip(keys, r)) for r in rows])


@auth_bp.route('/admin/rol', methods=['POST'])
def admin_cambiar_rol():
    """Cambiar rol de usuario (admin/usuario)."""
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403
    data     = request.get_json()
    telefono = data.get('telefono')
    nuevo_rol = data.get('rol')
    if nuevo_rol not in ('admin', 'usuario'):
        return jsonify({'error': 'Rol inválido'}), 400
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("UPDATE usuarios SET rol = %s WHERE telefono = %s", (nuevo_rol, telefono))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': f'Rol actualizado a {nuevo_rol}'})


@auth_bp.route('/admin/banear', methods=['POST'])
def admin_banear():
    """Banear o desbanear usuario."""
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403
    data     = request.get_json()
    telefono = data.get('telefono')
    baneado  = data.get('baneado', True)
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("UPDATE usuarios SET baneado = %s WHERE telefono = %s", (1 if baneado else 0, telefono))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Usuario ' + ('baneado' if baneado else 'desbaneado')})


@auth_bp.route('/puntos', methods=['GET'])
def mis_puntos():
    """Devuelve puntos del usuario y su historial."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    telefono = session['telefono']
    db  = get_db()
    cur = db.connection.cursor()

    cur.execute("SELECT puntos FROM usuarios WHERE telefono = %s", (telefono,))
    row = cur.fetchone()
    puntos = row[0] if row else 0

    cur.execute("""
        SELECT motivo, cantidad, fecha
        FROM puntos_historial
        WHERE telefono = %s
        ORDER BY fecha DESC
        LIMIT 20
    """, (telefono,))
    historial = [{'motivo': r[0], 'cantidad': r[1], 'fecha': str(r[2])}
                 for r in cur.fetchall()]

    # Cuántas publicaciones hoy
    cur.execute(
        "SELECT COUNT(*) FROM publicaciones WHERE telefono = %s AND fecha >= NOW() - INTERVAL 24 HOUR",
        (telefono,)
    )
    pubs_hoy = cur.fetchone()[0]

    cur.close()
    return jsonify({'puntos': puntos, 'pubs_hoy': pubs_hoy, 'historial': historial})
