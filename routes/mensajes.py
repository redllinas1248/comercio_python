from flask import Blueprint, request, jsonify, session
from db import get_db

msg_bp = Blueprint('mensajes', __name__, url_prefix='/api/mensajes')


@msg_bp.route('/conversaciones', methods=['GET'])
def conversaciones():
    """Lista las conversaciones del usuario en sesión."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    telefono = session['telefono']
    db = get_db()
    cur = db.connection.cursor()

    cur.execute("""
        SELECT DISTINCT
            IF(emisor = %s, receptor, emisor) AS contacto,
            (SELECT mensaje FROM mensajes m2
             WHERE (m2.emisor = %s AND m2.receptor = contacto)
                OR (m2.receptor = %s AND m2.emisor = contacto)
             ORDER BY fecha DESC LIMIT 1) AS ultimo_mensaje,
            (SELECT fecha FROM mensajes m3
             WHERE (m3.emisor = %s AND m3.receptor = contacto)
                OR (m3.receptor = %s AND m3.emisor = contacto)
             ORDER BY fecha DESC LIMIT 1) AS ultima_fecha
        FROM mensajes
        WHERE emisor = %s OR receptor = %s
    """, (telefono,)*7)

    rows = cur.fetchall()
    cur.close()

    result = []
    for contacto, ultimo, fecha in rows:
        result.append({
            'contacto': contacto,
            'ultimo_mensaje': ultimo,
            'fecha': str(fecha)
        })
    return jsonify(result)


@msg_bp.route('/<receptor>', methods=['GET'])
def hilo(receptor):
    """Mensajes entre el usuario en sesión y el receptor."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    emisor = session['telefono']
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT id, emisor, receptor, mensaje, fecha
        FROM mensajes
        WHERE (emisor = %s AND receptor = %s)
           OR (emisor = %s AND receptor = %s)
        ORDER BY fecha ASC
    """, (emisor, receptor, receptor, emisor))
    rows = cur.fetchall()
    cur.close()

    keys = ['id','emisor','receptor','mensaje','fecha']
    result = [dict(zip(keys, r)) for r in rows]
    for r in result:
        r['fecha'] = str(r['fecha'])
    return jsonify(result)


@msg_bp.route('', methods=['POST'])
def enviar():
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    data     = request.get_json()
    receptor = data.get('receptor', '').strip()
    mensaje  = data.get('mensaje', '').strip()
    emisor   = session['telefono']

    if not receptor or not mensaje:
        return jsonify({'error': 'Receptor y mensaje son obligatorios'}), 400

    db = get_db()
    cur = db.connection.cursor()
    cur.execute(
        "INSERT INTO mensajes (emisor, receptor, mensaje) VALUES (%s, %s, %s)",
        (emisor, receptor, mensaje)
    )
    db.connection.commit()
    nuevo_id = cur.lastrowid

    # Notificar al receptor
    cur.execute("SELECT nombre FROM usuarios WHERE telefono = %s", (emisor,))
    row = cur.fetchone()
    nombre_emisor = row[0] if row and row[0] else emisor

    # Solo crear notif si no hay una no leída reciente del mismo emisor
    cur.execute("""
        SELECT id FROM notificaciones
        WHERE telefono_destino = %s
          AND mensaje LIKE %s
          AND leida = 0
          AND fecha >= NOW() - INTERVAL 5 MINUTE
    """, (receptor, f'%{emisor}%'))

    if not cur.fetchone():
        cur.execute(
            "INSERT INTO notificaciones (telefono_destino, mensaje) VALUES (%s, %s)",
            (receptor, f'💬 Nuevo mensaje de {nombre_emisor}')
        )
        db.connection.commit()

    cur.close()
    return jsonify({'mensaje': 'Enviado', 'id': nuevo_id}), 201
