from flask import Blueprint, request, jsonify, current_app
from db import get_db
from security import require_api_admin, get_current_user
import html
import cloudinary.uploader
import os

dir_bp = Blueprint('directorio', __name__, url_prefix='/api/directorio')


def subir_imagen(archivo):
    """Sube una imagen a Cloudinary y devuelve la URL."""
    if not archivo:
        return None
    try:
        resultado = cloudinary.uploader.upload(
            archivo,
            folder='comercio/directorio',
            resource_type='image'
        )
        return resultado['secure_url']
    except Exception as e:
        current_app.logger.error(f"Error subiendo imagen directorio: {e}")
        return None


@dir_bp.route('', methods=['GET'])
def listar():
    db = get_db()
    cur = db.cursor()
    tipo = request.args.get('tipo')

    if tipo:
        cur.execute("""
            SELECT d.id, d.categoria, d.nombre, d.telefono, d.horario, d.direccion, 
                   d.icono, d.tipo, d.foto, d.descripcion_corta,
                   COALESCE(AVG(c.calificacion), 0) AS promedio,
                   COUNT(c.id) AS total_calificaciones
            FROM directorio d
            LEFT JOIN calificaciones_directorio c ON c.directorio_id = d.id
            WHERE d.activo = true AND d.tipo = %s
            GROUP BY d.id
            ORDER BY d.categoria, d.orden, d.nombre
        """, (tipo,))
    else:
        cur.execute("""
            SELECT d.id, d.categoria, d.nombre, d.telefono, d.horario, d.direccion, 
                   d.icono, d.tipo, d.foto, d.descripcion_corta,
                   COALESCE(AVG(c.calificacion), 0) AS promedio,
                   COUNT(c.id) AS total_calificaciones
            FROM directorio d
            LEFT JOIN calificaciones_directorio c ON c.directorio_id = d.id
            WHERE d.activo = true
            GROUP BY d.id
            ORDER BY d.categoria, d.orden, d.nombre
        """)

    rows = cur.fetchall()
    cur.close()

    keys = ['id', 'categoria', 'nombre', 'telefono', 'horario', 'direccion', 
            'icono', 'tipo', 'foto', 'descripcion_corta', 'promedio', 'total_calificaciones']
    grupos = {}
    for row in rows:
        item = dict(zip(keys, row))
        item['promedio'] = float(item['promedio'])
        item['total_calificaciones'] = int(item['total_calificaciones'])
        cat = item['categoria']
        if cat not in grupos:
            grupos[cat] = []
        grupos[cat].append(item)

    return jsonify(grupos)


@dir_bp.route('/<int:item_id>/calificar', methods=['POST'])
def calificar(item_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Debes iniciar sesión para calificar'}), 401

    data = request.get_json(silent=True) or {}
    calificacion = data.get('calificacion')
    if not calificacion or not isinstance(calificacion, int) or calificacion < 1 or calificacion > 5:
        return jsonify({'error': 'Calificación inválida (1-5)'}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM directorio WHERE id = %s AND activo = true", (item_id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Servicio no encontrado'}), 404

    telefono = user['telefono']
    cur.execute("""
        INSERT INTO calificaciones_directorio (directorio_id, usuario_telefono, calificacion)
        VALUES (%s, %s, %s)
        ON CONFLICT (directorio_id, usuario_telefono) 
        DO UPDATE SET calificacion = EXCLUDED.calificacion, fecha = CURRENT_TIMESTAMP
        RETURNING calificacion
    """, (item_id, telefono, calificacion))
    nueva_calif = cur.fetchone()[0]
    db.commit()
    cur.close()

    db2 = get_db()
    cur2 = db2.cursor()
    cur2.execute("""
        SELECT COALESCE(AVG(calificacion), 0), COUNT(*)
        FROM calificaciones_directorio
        WHERE directorio_id = %s
    """, (item_id,))
    promedio, total = cur2.fetchone()
    cur2.close()

    return jsonify({
        'mensaje': 'Calificación guardada',
        'promedio': float(promedio),
        'total': int(total),
        'tu_calificacion': nueva_calif
    })


@dir_bp.route('/<int:item_id>/mi-calificacion', methods=['GET'])
def mi_calificacion(item_id):
    user = get_current_user()
    if not user:
        return jsonify({'calificacion': None})
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT calificacion FROM calificaciones_directorio
        WHERE directorio_id = %s AND usuario_telefono = %s
    """, (item_id, user['telefono']))
    row = cur.fetchone()
    cur.close()
    return jsonify({'calificacion': row[0] if row else None})


@dir_bp.route('', methods=['POST'])
def crear():
    _, error = require_api_admin()
    if error:
        return error

    # Leer datos del formulario (multipart/form-data)
    data = request.form
    foto_file = request.files.get('foto')

    foto_url = None
    if foto_file and foto_file.filename:
        foto_url = subir_imagen(foto_file)
        if not foto_url:
            return jsonify({'error': 'Error al subir la imagen'}), 500

    campos = ['categoria', 'nombre', 'telefono', 'horario', 'direccion', 'icono', 'orden', 'tipo', 'descripcion_corta']
    valores = [data.get(c, '') or (0 if c == 'orden' else '') for c in campos]
    if not valores[7]:
        valores[7] = 'general'

    # Insertar
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO directorio (categoria, nombre, telefono, horario, direccion, icono, orden, tipo, foto, descripcion_corta)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    """, valores + [foto_url])
    nuevo_id = cur.fetchone()[0]
    db.commit()
    cur.close()
    return jsonify({'mensaje': 'Creado', 'id': nuevo_id}), 201


@dir_bp.route('/<int:item_id>', methods=['PUT'])
def actualizar(item_id):
    _, error = require_api_admin()
    if error:
        return error

    data = request.form
    foto_file = request.files.get('foto')

    # Obtener datos actuales para saber si hay foto antigua (opcional)
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT foto FROM directorio WHERE id = %s", (item_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return jsonify({'error': 'No encontrado'}), 404
    foto_actual = row[0]

    # Subir nueva foto si se envió
    foto_url = foto_actual
    if foto_file and foto_file.filename:
        nueva_foto = subir_imagen(foto_file)
        if nueva_foto:
            foto_url = nueva_foto
        else:
            return jsonify({'error': 'Error al subir la imagen'}), 500

    campos = ['categoria', 'nombre', 'telefono', 'horario', 'direccion', 'icono', 'orden', 'tipo', 'descripcion_corta']
    updates = {}
    for c in campos:
        if c in data:
            updates[c] = data[c] or (0 if c == 'orden' else '')
    if foto_url:
        updates['foto'] = foto_url

    if not updates:
        return jsonify({'error': 'Nada que actualizar'}), 400

    set_clause = ', '.join(f"{k} = %s" for k in updates)
    valores = list(updates.values()) + [item_id]

    cur = db.cursor()
    cur.execute(f"UPDATE directorio SET {set_clause} WHERE id = %s", valores)
    db.commit()
    cur.close()
    return jsonify({'mensaje': 'Actualizado'})


@dir_bp.route('/<int:item_id>', methods=['DELETE'])
def eliminar(item_id):
    _, error = require_api_admin()
    if error:
        return error
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM directorio WHERE id = %s", (item_id,))
    db.commit()
    cur.close()
    return jsonify({'mensaje': 'Eliminado'})


@dir_bp.route('/<int:item_id>/toggle', methods=['POST'])
def toggle(item_id):
    _, error = require_api_admin()
    if error:
        return error
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE directorio SET activo = NOT activo WHERE id = %s", (item_id,))
    db.commit()
    cur.close()
    return jsonify({'mensaje': 'Actualizado'})