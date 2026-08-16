from flask import Blueprint, request, jsonify, render_template, current_app
from db import get_db
from security import require_api_admin, get_current_user
import html
from routes.push import enviar_notificacion_a_todos

transmisiones_bp = Blueprint('transmisiones', __name__, url_prefix='/api/transmisiones')


def validar_url(url):
    if not url:
        return False
    url = url.strip()
    if len(url) == 11 and url.isalnum() and '-' in url:
        return True
    if url.startswith('https://www.youtube.com/') or url.startswith('https://youtu.be/'):
        return True
    if url.startswith('http://') or url.startswith('https://'):
        return True
    return False


def obtener_embed_url(url):
    url = url.strip()
    if len(url) == 11 and url.isalnum() and '-' in url:
        return f"https://www.youtube.com/embed/{url}"
    if 'youtube.com/watch?v=' in url:
        video_id = url.split('v=')[1].split('&')[0]
        return f"https://www.youtube.com/embed/{video_id}"
    if 'youtu.be/' in url:
        video_id = url.split('youtu.be/')[1].split('?')[0]
        return f"https://www.youtube.com/embed/{video_id}"
    if 'youtube.com/embed/' in url:
        return url
    if 'youtube.com/live_stream?channel=' in url:
        return url
    return url


@transmisiones_bp.route('/publicas', methods=['GET'])
def listar_publicas():
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT id, titulo, descripcion, url, categoria, destacada, orden
        FROM transmisiones
        WHERE activo = 1
        ORDER BY destacada DESC, orden ASC, fecha_creacion DESC
    """)
    rows = cur.fetchall()
    cur.close()
    keys = ['id', 'titulo', 'descripcion', 'url', 'categoria', 'destacada', 'orden']
    result = [dict(zip(keys, row)) for row in rows]
    return jsonify(result)


@transmisiones_bp.route('/destacada', methods=['GET'])
def obtener_destacada():
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT id, titulo, descripcion, url, categoria
        FROM transmisiones
        WHERE activo = 1 AND destacada = 1
        ORDER BY orden ASC, fecha_creacion DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    if not row:
        return jsonify({'error': 'No hay transmisión destacada'}), 404
    keys = ['id', 'titulo', 'descripcion', 'url', 'categoria']
    return jsonify(dict(zip(keys, row)))


@transmisiones_bp.route('', methods=['GET'])
def listar_admin():
    _, error = require_api_admin()
    if error:
        return error
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT id, titulo, descripcion, url, categoria, destacada, activo, orden, fecha_creacion
        FROM transmisiones
        ORDER BY orden ASC, fecha_creacion DESC
    """)
    rows = cur.fetchall()
    cur.close()
    keys = ['id', 'titulo', 'descripcion', 'url', 'categoria', 'destacada', 'activo', 'orden', 'fecha_creacion']
    result = [dict(zip(keys, row)) for row in rows]
    for r in result:
        r['fecha_creacion'] = str(r['fecha_creacion'])
    return jsonify(result)


@transmisiones_bp.route('', methods=['POST'])
def crear():
    _, error = require_api_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    
    titulo = html.escape(str(data.get('titulo', '').strip()))
    descripcion = html.escape(str(data.get('descripcion', '').strip()))[:500]
    url = str(data.get('url', '').strip())
    categoria = data.get('categoria', 'noticias')
    destacada = 1 if data.get('destacada', False) else 0
    activo = 1 if data.get('activo', True) else 0
    orden = int(data.get('orden', 0))
    
    if not titulo or not url:
        return jsonify({'error': 'Título y URL son obligatorios'}), 400
    if categoria not in ('noticias', 'deportes', 'eventos'):
        return jsonify({'error': 'Categoría inválida'}), 400
    if not validar_url(url):
        return jsonify({'error': 'URL inválida'}), 400
    
    if destacada:
        db = get_db()
        cur = db.connection.cursor()
        cur.execute("UPDATE transmisiones SET destacada = 0")
        db.connection.commit()
        cur.close()
    
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        INSERT INTO transmisiones (titulo, descripcion, url, categoria, destacada, activo, orden)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (titulo, descripcion, url, categoria, destacada, activo, orden))
    db.connection.commit()
    nuevo_id = cur.lastrowid
    cur.close()
    
    # Enviar notificación push si la transmisión está activa o destacada
    if activo or destacada:
        try:
            enviar_notificacion_a_todos(
                title=f"📺 {titulo}",
                body=descripcion or "¡Transmisión en vivo!",
                url="/transmisiones"
            )
        except Exception as e:
            current_app.logger.error(f"Error enviando notificación: {e}")
    
    return jsonify({'mensaje': 'Transmisión creada', 'id': nuevo_id}), 201


@transmisiones_bp.route('/<int:item_id>', methods=['PUT'])
def actualizar(item_id):
    _, error = require_api_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    
    # Obtener estado actual antes de actualizar
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("SELECT activo, destacada, titulo FROM transmisiones WHERE id = %s", (item_id,))
    current = cur.fetchone()
    cur.close()
    if not current:
        return jsonify({'error': 'No encontrada'}), 404
    current_activo, current_destacada, current_titulo = current
    
    campos_permitidos = ['titulo', 'descripcion', 'url', 'categoria', 'destacada', 'activo', 'orden']
    updates = {}
    for campo in campos_permitidos:
        if campo in data:
            if campo == 'titulo':
                updates[campo] = html.escape(str(data[campo]).strip())
            elif campo == 'descripcion':
                updates[campo] = html.escape(str(data[campo]).strip())[:500]
            elif campo == 'url':
                url = str(data[campo]).strip()
                if not validar_url(url):
                    return jsonify({'error': 'URL inválida'}), 400
                updates[campo] = url
            elif campo == 'categoria':
                if data[campo] not in ('noticias', 'deportes', 'eventos'):
                    return jsonify({'error': 'Categoría inválida'}), 400
                updates[campo] = data[campo]
            elif campo == 'destacada':
                updates[campo] = 1 if data[campo] else 0
            elif campo == 'activo':
                updates[campo] = 1 if data[campo] else 0
            elif campo == 'orden':
                updates[campo] = int(data[campo] or 0)
    
    if not updates:
        return jsonify({'error': 'Nada que actualizar'}), 400
    
    if updates.get('destacada') == 1:
        cur = db.connection.cursor()
        cur.execute("UPDATE transmisiones SET destacada = 0 WHERE id != %s", (item_id,))
        db.connection.commit()
        cur.close()
    
    set_clause = ', '.join(f"{k} = %s" for k in updates)
    valores = list(updates.values()) + [item_id]
    # Agregar actualización manual de fecha_actualizacion
    set_clause += ", fecha_actualizacion = NOW()"
    
    cur = db.connection.cursor()
    cur.execute(f"UPDATE transmisiones SET {set_clause} WHERE id = %s", valores)
    db.connection.commit()
    cur.close()
    
    # Verificar si se activó o destacó después de la actualización
    nuevo_activo = updates.get('activo', current_activo)
    nuevo_destacada = updates.get('destacada', current_destacada)
    nuevo_titulo = updates.get('titulo', current_titulo)
    
    if (nuevo_activo and not current_activo) or (nuevo_destacada and not current_destacada):
        try:
            enviar_notificacion_a_todos(
                title=f"📺 {nuevo_titulo}",
                body=data.get('descripcion', '¡Transmisión en vivo!'),
                url="/transmisiones"
            )
        except Exception as e:
            current_app.logger.error(f"Error enviando notificación: {e}")
    
    return jsonify({'mensaje': 'Transmisión actualizada'})


@transmisiones_bp.route('/<int:item_id>', methods=['DELETE'])
def eliminar(item_id):
    _, error = require_api_admin()
    if error:
        return error
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("DELETE FROM transmisiones WHERE id = %s", (item_id,))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Transmisión eliminada'})


@transmisiones_bp.route('/reordenar', methods=['POST'])
def reordenar():
    _, error = require_api_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    ordenes = data.get('ordenes', [])
    if not ordenes:
        return jsonify({'error': 'No se enviaron órdenes'}), 400
    db = get_db()
    cur = db.connection.cursor()
    for item in ordenes:
        cur.execute("UPDATE transmisiones SET orden = %s WHERE id = %s", (item['orden'], item['id']))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Orden actualizado'})