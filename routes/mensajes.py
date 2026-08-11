from flask import Blueprint, request, jsonify, session
from db import get_db
import html as html_lib
from security import get_current_user, valid_phone

msg_bp = Blueprint('mensajes', __name__, url_prefix='/api/mensajes')


@msg_bp.route('/conversaciones', methods=['GET'])
def conversaciones():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    telefono = user['telefono']
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
    user = get_current_user()
    if not user:
        return jsonify({'error': 'No autenticado'}), 401
    if not valid_phone(receptor):
        return jsonify({'error': 'Contacto inválido'}), 400

    emisor = user['telefono']
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
    user = get_current_user()
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    data     = request.get_json(silent=True) or {}
    receptor = str(data.get('receptor') or '').strip()
    mensaje  = html_lib.escape(str(data.get('mensaje') or '').strip())[:2000]
    emisor   = user['telefono']

    if not valid_phone(receptor):
        return jsonify({'error': 'Receptor inválido'}), 400
    if receptor == emisor:
        return jsonify({'error': 'No puedes enviarte mensajes a ti mismo'}), 400
    if not mensaje:
        return jsonify({'error': 'Receptor y mensaje son obligatorios'}), 400

    db = get_db()
    cur = db.connection.cursor()
    cur.execute(
        "INSERT INTO mensajes (emisor, receptor, mensaje) VALUES (%s, %s, %s)",
        (emisor, receptor, mensaje)
    )
    db.connection.commit()
    nuevo_id = cur.lastrowid

    cur.execute("SELECT nombre FROM usuarios WHERE telefono = %s", (emisor,))
    row = cur.fetchone()
    nombre_emisor = row[0] if row and row[0] else emisor

    cur.execute("""
        SELECT id FROM notificaciones
        WHERE telefono_destino = %s AND mensaje LIKE %s
          AND leida = 0 AND fecha >= NOW() - INTERVAL 5 MINUTE
    """, (receptor, f'%{emisor}%'))

    if not cur.fetchone():
        cur.execute(
            "INSERT INTO notificaciones (telefono_destino, mensaje) VALUES (%s, %s)",
            (receptor, f'Nuevo mensaje de {nombre_emisor}')
        )
        db.connection.commit()

    cur.close()
    return jsonify({'mensaje': 'Enviado', 'id': nuevo_id}), 201


@msg_bp.route('/conversacion/<contacto>', methods=['DELETE'])
def eliminar_conversacion(contacto):
    """Eliminar todos los mensajes de una conversación."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'No autenticado'}), 401
    if not valid_phone(contacto):
        return jsonify({'error': 'Contacto inválido'}), 400

    telefono = user['telefono']
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        DELETE FROM mensajes
        WHERE (emisor = %s AND receptor = %s)
           OR (emisor = %s AND receptor = %s)
    """, (telefono, contacto, contacto, telefono))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Conversación eliminada'})
