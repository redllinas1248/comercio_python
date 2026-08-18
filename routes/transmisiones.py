from flask import Blueprint, request, jsonify, current_app
from db import get_db
from security import require_api_admin
import html
from routes.push import enviar_notificacion_a_todos
import re

transmisiones_bp = Blueprint('transmisiones', __name__, url_prefix='/api/transmisiones')


def validar_url(url):
    """Valida que la URL sea de YouTube o un ID válido."""
    if not url:
        return False
    url = url.strip()
    
    # ID de video de 11 caracteres (alfanumérico con guiones)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return True
    
    # URL de YouTube en cualquier formato
    youtube_patterns = [
        r'^https?://(www\.)?youtube\.com/embed/',
        r'^https?://(www\.)?youtube\.com/watch\?v=',
        r'^https?://youtu\.be/',
        r'^https?://(www\.)?youtube\.com/live/',
        r'^https?://(www\.)?youtube\.com/live_stream\?channel=',
        r'^https?://(www\.)?youtube\.com/@',
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    
    # Cualquier URL que empiece con http/https (para otros servicios)
    if url.startswith('http://') or url.startswith('https://'):
        return True
    
    return False


def obtener_embed_url(url):
    """Convierte cualquier formato de URL de YouTube a embed URL."""
    url = url.strip()
    
    # Si es un ID de video de 11 caracteres
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return f"https://www.youtube.com/embed/{url}"
    
    # Si es una URL de canal en vivo (live_stream?channel=...)
    if 'live_stream?channel=' in url:
        # Si la URL ya tiene el formato correcto, devolverla
        if url.startswith('https://www.youtube.com/embed/live_stream?channel='):
            return url
        # Si es un enlace directo al canal en vivo
        channel_id = url.split('channel=')[1].split('&')[0]
        return f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
    
    # Si es una URL de YouTube normal
    if 'youtube.com/watch?v=' in url:
        video_id = url.split('v=')[1].split('&')[0]
        return f"https://www.youtube.com/embed/{video_id}"
    
    if 'youtu.be/' in url:
        video_id = url.split('youtu.be/')[1].split('?')[0]
        return f"https://www.youtube.com/embed/{video_id}"
    
    if 'youtube.com/embed/' in url:
        return url  # Ya es embed
    
    if 'youtube.com/live/' in url:
        video_id = url.split('live/')[1].split('?')[0]
        return f"https://www.youtube.com/embed/{video_id}"
    
    if 'youtube.com/@' in url:
        # Es un canal, extraer el nombre del canal
        channel = url.split('@')[1].split('/')[0].split('?')[0]
        return f"https://www.youtube.com/embed/live_stream?channel=@{channel}"
    
    # Si no, devolver la URL tal cual (para otros servicios)
    return url


@transmisiones_bp.route('/publicas', methods=['GET'])
def listar_publicas():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, titulo, descripcion, url, categoria, destacada, orden
        FROM transmisiones
        WHERE activo = true
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
    cur = db.cursor()
    cur.execute("""
        SELECT id, titulo, descripcion, url, categoria
        FROM transmisiones
        WHERE activo = true AND destacada = true
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
    cur = db.cursor()
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

    # Convertir la URL a formato embed
    embed_url = obtener_embed_url(url)

    db = get_db()
    cur = db.cursor()

    if destacada:
        cur.execute("UPDATE transmisiones SET destacada = false")
        db.commit()

    cur.execute("""
        INSERT INTO transmisiones (titulo, descripcion, url, categoria, destacada, activo, orden)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    """, (titulo, descripcion, embed_url, categoria, destacada, activo, orden))
    nuevo_id = cur.fetchone()[0]
    db.commit()
    cur.close()

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

    db = get_db()
    cur = db.cursor()
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
                updates[campo] = obtener_embed_url(url)
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

    cur = db.cursor()

    if updates.get('destacada') == 1:
        cur.execute("UPDATE transmisiones SET destacada = false WHERE id != %s", (item_id,))
        db.commit()

    set_clause = ', '.join(f"{k} = %s" for k in updates)
    valores = list(updates.values()) + [item_id]
    set_clause += ", fecha_actualizacion = NOW()"

    cur.execute(f"UPDATE transmisiones SET {set_clause} WHERE id = %s", valores)
    db.commit()
    cur.close()

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
    cur = db.cursor()
    cur.execute("DELETE FROM transmisiones WHERE id = %s", (item_id,))
    db.commit()
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
    cur = db.cursor()
    for item in ordenes:
        cur.execute("UPDATE transmisiones SET orden = %s WHERE id = %s", (item['orden'], item['id']))
    db.commit()
    cur.close()
    return jsonify({'mensaje': 'Orden actualizado'})