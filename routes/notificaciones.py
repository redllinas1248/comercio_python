from flask import Blueprint, jsonify, session
from db import get_db

notif_bp = Blueprint('notificaciones', __name__, url_prefix='/api/notificaciones')


@notif_bp.route('', methods=['GET'])
def listar():
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    telefono = session['telefono']
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT id, mensaje, leida, fecha
        FROM notificaciones
        WHERE telefono_destino = %s
        ORDER BY fecha DESC
        LIMIT 50
    """, (telefono,))
    rows = cur.fetchall()
    cur.close()

    keys = ['id','mensaje','leida','fecha']
    result = [dict(zip(keys, r)) for r in rows]
    for r in result:
        r['fecha'] = str(r['fecha'])
    return jsonify(result)


@notif_bp.route('/marcar-leidas', methods=['POST'])
def marcar_leidas():
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    telefono = session['telefono']
    db = get_db()
    cur = db.connection.cursor()
    cur.execute(
        "UPDATE notificaciones SET leida = 1 WHERE telefono_destino = %s AND leida = 0",
        (telefono,)
    )
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Marcadas como leídas'})


@notif_bp.route('/no-leidas', methods=['GET'])
def no_leidas():
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    telefono = session['telefono']
    db = get_db()
    cur = db.connection.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM notificaciones WHERE telefono_destino = %s AND leida = 0",
        (telefono,)
    )
    total = cur.fetchone()[0]
    cur.close()
    return jsonify({'no_leidas': total})
