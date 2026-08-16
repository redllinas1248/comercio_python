from flask import Blueprint, request, jsonify
from db import get_db
from security import require_api_admin

dir_bp = Blueprint('directorio', __name__, url_prefix='/api/directorio')


@dir_bp.route('', methods=['GET'])
def listar():
    db = get_db()
    cur = db.cursor()

    tipo = request.args.get('tipo')

    if tipo:
        cur.execute("""
            SELECT id, categoria, nombre, telefono, horario, direccion, icono, tipo
            FROM directorio
            WHERE activo = true AND tipo = %s
            ORDER BY categoria, orden, nombre
        """, (tipo,))
    else:
        cur.execute("""
            SELECT id, categoria, nombre, telefono, horario, direccion, icono, tipo
            FROM directorio
            WHERE activo = true
            ORDER BY categoria, orden, nombre
        """)

    rows = cur.fetchall()
    cur.close()

    keys = ['id', 'categoria', 'nombre', 'telefono', 'horario', 'direccion', 'icono', 'tipo']
    grupos = {}
    for row in rows:
        item = dict(zip(keys, row))
        cat = item['categoria']
        if cat not in grupos:
            grupos[cat] = []
        grupos[cat].append(item)

    return jsonify(grupos)


@dir_bp.route('', methods=['POST'])
def crear():
    _, error = require_api_admin()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    campos = ['categoria', 'nombre', 'telefono', 'horario', 'direccion', 'icono', 'orden', 'tipo']
    valores = [data.get(c, '') or (0 if c == 'orden' else '') for c in campos]
    if not valores[7]:
        valores[7] = 'general'

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO directorio (categoria, nombre, telefono, horario, direccion, icono, orden, tipo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
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
    campos = ['categoria', 'nombre', 'telefono', 'horario', 'direccion', 'icono', 'orden', 'tipo']
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