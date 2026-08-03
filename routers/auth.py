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

    cur.execute(
        "INSERT INTO usuarios (telefono, usuario, nombre, pin) VALUES (%s, %s, %s, %s)",
        (telefono, usuario, nombre or None, pin_hash)
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
