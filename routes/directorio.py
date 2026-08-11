from flask import Blueprint, request, jsonify, session
from db import get_db

dir_bp = Blueprint('directorio', __name__, url_prefix='/api/directorio')

# Categorías que pertenecen a Servicios
CATEGORIAS_SERVICIOS = {
    'plomero', 'plomería', 'electricista', 'electricidad', 'carpintero',
    'carpintería', 'pintor', 'pintura', 'albañil', 'construcción',
    'mecánico', 'mecánica', 'jardinero', 'jardinería', 'servicios',
    'servicio', 'técnico', 'reparación', 'reparaciones', 'otros servicios'
}


def es_servicio(categoria):
    return any(s in categoria.lower() for s in CATEGORIAS_SERVICIOS)


@dir_bp.route('', methods=['GET'])
def listar():
    """Lista registros activos. Filtro: ?tipo=servicios o ?tipo=emergencias"""
    tipo = request.args.get('tipo', '').lower()

    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT id, categoria, nombre, telefono, horario, direccion, icono
        FROM directorio
        WHERE activo = 1
        ORDER BY categoria, orden, nombre
    """)
    rows = cur.fetchall()
    cur.close()

    keys = ['id','categoria','nombre','telefono','horario','direccion','icono']
    grupos = {}
    for row in rows:
        item = dict(zip(keys, row))
        cat  = item['categoria']

        # Filtrar según tipo
        if tipo == 'servicios' and not es_servicio(cat):
            continue
        if tipo == 'emergencias' and es_servicio(cat):
            continue

        if cat not in grupos:
            grupos[cat] = []
        grupos[cat].append(item)

    return jsonify(grupos)


@dir_bp.route('', methods=['POST'])
def crear():
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403
    data   = request.get_json()
    campos = ['categoria','nombre','telefono','horario','direccion','icono','orden']
    valores = [data.get(c, '') or (0 if c == 'orden' else '') for c in campos]

    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        INSERT INTO directorio (categoria, nombre, telefono, horario, direccion, icono, orden)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, valores)
    db.connection.commit()
    nuevo_id = cur.lastrowid
    cur.close()
    return jsonify({'mensaje': 'Creado', 'id': nuevo_id}), 201


@dir_bp.route('/<int:item_id>', methods=['PUT'])
def actualizar(item_id):
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403
    data    = request.get_json()
    campos  = ['categoria','nombre','telefono','horario','direccion','icono','orden']
    updates = {k: data[k] for k in campos if k in data}
    if not updates:
        return jsonify({'error': 'Nada que actualizar'}), 400

    set_clause = ', '.join(f"{k} = %s" for k in updates)
    valores    = list(updates.values()) + [item_id]

    db  = get_db()
    cur = db.connection.cursor()
    cur.execute(f"UPDATE directorio SET {set_clause} WHERE id = %s", valores)
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Actualizado'})


@dir_bp.route('/<int:item_id>', methods=['DELETE'])
def eliminar(item_id):
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("DELETE FROM directorio WHERE id = %s", (item_id,))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Eliminado'})


@dir_bp.route('/<int:item_id>/toggle', methods=['POST'])
def toggle(item_id):
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("UPDATE directorio SET activo = NOT activo WHERE id = %s", (item_id,))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Actualizado'})
