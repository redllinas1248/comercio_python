from flask import Blueprint, request, jsonify
from db import get_db
from security import require_api_admin, get_current_user
import html

dir_bp = Blueprint('directorio', __name__, url_prefix='/api/directorio')


@dir_bp.route('', methods=['GET'])
def listar():
    """Lista todos los registros activos agrupados por categoría, con calificaciones."""
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
    """Califica un servicio con 1-5 estrellas."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Debes iniciar sesión para calificar'}), 401

    data = request.get_json(silent=True) or {}
    calificacion = data.get('calificacion')
    if not calificacion or not isinstance(calificacion, int) or calificacion < 1 or calificacion > 5:
        return jsonify({'error': 'Calificación inválida (1-5)'}), 400

    db = get_db()
    cur = db.cursor()

    # Verificar que el directorio existe
    cur.execute("SELECT id FROM directorio WHERE id = %s AND activo = true", (item_id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Servicio no encontrado'}), 404

    telefono = user['telefono']

    # Insertar o actualizar calificación
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

    # Calcular nuevo promedio
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
    """Obtiene la calificación que el usuario actual dio a un servicio."""
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
    data = request.get_json(silent=True) or {}
    campos = ['categoria', 'nombre', 'telefono', 'horario', 'direccion', 'icono', 'orden', 'tipo', 'foto', 'descripcion_corta']
    valores = [data.get(c, '') or (0 if c == 'orden' else '') for c in campos]
    if not valores[7]:
        valores[7] = 'general'

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO directorio (categoria, nombre, telefono, horario, direccion, icono, orden, tipo, foto, descripcion_corta)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    """, valores)
    nuevo_id = cur.fetchone()[0]
    db.commit()
    cur.close()
    return jsonify({'mensaje': 'Creado', 'id': nuevo_id}), 201


@dir_bp.route('/<int:item_id>', methods=['PUT'])
def actualizar(item_id):
    _, error = require_api_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    campos = ['categoria', 'nombre', 'telefono', 'horario', 'direccion', 'icono', 'orden', 'tipo', 'foto', 'descripcion_corta']
    updates = {k: data[k] for k in campos if k in data}
    if not updates:
        return jsonify({'error': 'Nada que actualizar'}), 400

    set_clause = ', '.join(f"{k} = %s" for k in updates)
    valores = list(updates.values()) + [item_id]

    db = get_db()
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