from flask import Blueprint, request, jsonify, session
from db import get_db

likes_bp = Blueprint('likes', __name__, url_prefix='/api/likes')

REACCIONES_VALIDAS = {'like', 'love', 'angry', 'wow', 'sad'}


@likes_bp.route('/<int:pub_id>', methods=['GET'])
def listar(pub_id):
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT reaccion, COUNT(*) as total
        FROM likes WHERE publicacion_id = %s
        GROUP BY reaccion
    """, (pub_id,))
    rows = cur.fetchall()
    cur.close()
    return jsonify([{'reaccion': r[0], 'total': r[1]} for r in rows])


@likes_bp.route('', methods=['POST'])
def reaccionar():
    """Dar o quitar reacción (toggle)."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    data      = request.get_json()
    pub_id    = data.get('publicacion_id')
    reaccion  = data.get('reaccion', 'like')
    telefono  = session['telefono']

    if reaccion not in REACCIONES_VALIDAS:
        return jsonify({'error': 'Reacción no válida'}), 400

    db = get_db()
    cur = db.connection.cursor()

    # Ver si ya reaccionó
    cur.execute(
        "SELECT id, reaccion FROM likes WHERE telefono = %s AND publicacion_id = %s",
        (telefono, pub_id)
    )
    existente = cur.fetchone()

    if existente:
        if existente[1] == reaccion:
            # Misma reacción → quitar (toggle off)
            cur.execute("DELETE FROM likes WHERE id = %s", (existente[0],))
            db.connection.commit()
            cur.close()
            return jsonify({'accion': 'quitado', 'reaccion': reaccion})
        else:
            # Cambiar reacción
            cur.execute("UPDATE likes SET reaccion = %s WHERE id = %s", (reaccion, existente[0]))
            db.connection.commit()
            cur.close()
            return jsonify({'accion': 'cambiado', 'reaccion': reaccion})
    else:
        # Nueva reacción
        cur.execute(
            "INSERT INTO likes (telefono, publicacion_id, reaccion) VALUES (%s, %s, %s)",
            (telefono, pub_id, reaccion)
        )
        db.connection.commit()

        # Notificar al dueño
        cur.execute("SELECT telefono FROM publicaciones WHERE id = %s", (pub_id,))
        row = cur.fetchone()
        if row and row[0] != telefono:
            emojis = {'like': '👍', 'love': '❤️', 'angry': '😠', 'wow': '😮', 'sad': '😢'}
            cur.execute(
                "INSERT INTO notificaciones (telefono_destino, mensaje) VALUES (%s, %s)",
                (row[0], f"{emojis.get(reaccion, '👍')} Le dieron {reaccion} a tu publicación")
            )
            db.connection.commit()

        cur.close()
        return jsonify({'accion': 'agregado', 'reaccion': reaccion}), 201
