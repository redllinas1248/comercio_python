import os, time
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from db import get_db

pub_bp = Blueprint('publicaciones', __name__, url_prefix='/api/publicaciones')


def allowed_file(filename):
    exts = current_app.config.get('ALLOWED_EXTENSIONS', {'png','jpg','jpeg','gif','webp'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in exts

def allowed_video(filename):
    exts = current_app.config.get('ALLOWED_VIDEO_EXTS', {'mp4','mov','webm','avi'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in exts


@pub_bp.route('', methods=['GET'])
def listar():
    """Lista publicaciones con filtro opcional por categoría."""
    categoria_id = request.args.get('categoria_id')
    telefono_filtro = request.args.get('telefono')
    limite = int(request.args.get('limite', 20))
    offset = int(request.args.get('offset', 0))

    db = get_db()
    cur = db.connection.cursor()

    condiciones = []
    params = []

    if categoria_id:
        condiciones.append("p.categoria_id = %s")
        params.append(categoria_id)
    if telefono_filtro:
        condiciones.append("p.telefono = %s")
        params.append(telefono_filtro)

    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    cur.execute(f"""
        SELECT p.id, p.telefono, p.contenido, p.fecha, p.categoria_id,
               c.nombre AS categoria,
               u.nombre AS autor, u.foto AS autor_foto, u.telefono AS tel_autor, u.localidad AS comunidad,
               p.precio, p.destacada,
               (SELECT COUNT(*) FROM likes l WHERE l.publicacion_id = p.id) AS total_likes,
               (SELECT COUNT(*) FROM comentarios co WHERE co.publicacion_id = p.id) AS total_comentarios
        FROM publicaciones p
        LEFT JOIN categorias c ON c.id = p.categoria_id
        LEFT JOIN usuarios u ON u.telefono = p.telefono
        {where}
        ORDER BY p.destacada DESC, p.fecha DESC
        LIMIT %s OFFSET %s
    """, params + [limite, offset])

    rows = cur.fetchall()
    keys = ['id','telefono','contenido','fecha','categoria_id','categoria',
            'autor','autor_foto','tel_autor','comunidad','precio','destacada','total_likes','total_comentarios']
    publicaciones = [dict(zip(keys, r)) for r in rows]

    # Adjuntar imágenes a cada publicación
    for pub in publicaciones:
        cur.execute(
            "SELECT ruta FROM publicaciones_imagenes WHERE publicacion_id = %s",
            (pub['id'],)
        )
        pub['imagenes'] = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT ruta FROM publicaciones_videos WHERE publicacion_id = %s", (pub['id'],))
        pub['videos'] = [row[0] for row in cur.fetchall()]
        pub['fecha'] = str(pub['fecha'])

    cur.close()
    return jsonify(publicaciones)


@pub_bp.route('/<int:pub_id>', methods=['GET'])
def detalle(pub_id):
    """Detalle de una publicación."""
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT p.id, p.telefono, p.contenido, p.fecha, p.categoria_id,
               c.nombre AS categoria, u.nombre AS autor, u.foto AS autor_foto,
               u.telefono AS tel_autor, p.precio
        FROM publicaciones p
        LEFT JOIN categorias c ON c.id = p.categoria_id
        LEFT JOIN usuarios u ON u.telefono = p.telefono
        WHERE p.id = %s
    """, (pub_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({'error': 'No encontrada'}), 404

    keys = ['id','telefono','contenido','fecha','categoria_id','categoria','autor','autor_foto','tel_autor','precio','comunidad']
    pub = dict(zip(keys, row))
    pub['fecha'] = str(pub['fecha'])

    cur.execute("SELECT ruta FROM publicaciones_imagenes WHERE publicacion_id = %s", (pub_id,))
    pub['imagenes'] = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT ruta FROM publicaciones_videos WHERE publicacion_id = %s", (pub_id,))
    pub['videos'] = [r[0] for r in cur.fetchall()]
    cur.close()
    return jsonify(pub)


@pub_bp.route('', methods=['POST'])
def crear():
    """Crear publicación con texto e imágenes opcionales."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    contenido    = request.form.get('contenido', '').strip()
    categoria_id = request.form.get('categoria_id')
    precio       = request.form.get('precio', '').strip() or None
    telefono     = session['telefono']

    if not contenido:
        return jsonify({'error': 'El contenido es obligatorio'}), 400

    db  = get_db()
    cur = db.connection.cursor()

    # Verificar limite de 2 publicaciones en las ultimas 24 horas
    cur.execute(
        "SELECT COUNT(*) FROM publicaciones WHERE telefono = %s AND fecha >= NOW() - INTERVAL 24 HOUR",
        (telefono,)
    )
    count_hoy = cur.fetchone()[0]
    if count_hoy >= 2:
        cur.close()
        return jsonify({'error': '⏳ Llegaste al límite de 2 publicaciones por día. Intenta mañana.'}), 429

    cur.execute(
        "INSERT INTO publicaciones (telefono, contenido, categoria_id, precio) VALUES (%s, %s, %s, %s)",
        (telefono, contenido, categoria_id, precio)
    )
    db.connection.commit()
    pub_id = cur.lastrowid

    # Sistema de puntos: 1 punto por cada 2 publicaciones totales
    cur.execute("SELECT COUNT(*) FROM publicaciones WHERE telefono = %s", (telefono,))
    total_pubs = cur.fetchone()[0]
    if total_pubs % 2 == 0:
        cur.execute("UPDATE usuarios SET puntos = puntos + 1 WHERE telefono = %s", (telefono,))
        cur.execute(
            "INSERT INTO puntos_historial (telefono, motivo, cantidad) VALUES (%s, %s, 1)",
            (telefono, "2 publicaciones completadas (" + str(total_pubs) + " total)")
        )
        db.connection.commit()

    # Guardar imágenes
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)

    for img in request.files.getlist('imagenes'):
        if img and img.filename and allowed_file(img.filename):
            filename = f"{int(time.time())}_{secure_filename(img.filename)}"
            ruta     = os.path.join('img', 'posts', filename)
            img.save(os.path.join('static', ruta))
            cur.execute(
                "INSERT INTO publicaciones_imagenes (publicacion_id, ruta) VALUES (%s, %s)",
                (pub_id, ruta)
            )

    # Guardar videos
    video_folder = current_app.config['VIDEO_FOLDER']
    os.makedirs(video_folder, exist_ok=True)

    for vid in request.files.getlist('videos'):
        if vid and vid.filename and allowed_video(vid.filename):
            filename = f"{int(time.time())}_{secure_filename(vid.filename)}"
            ruta     = os.path.join('videos', 'posts', filename)
            vid.save(os.path.join('static', ruta))
            cur.execute(
                "INSERT INTO publicaciones_videos (publicacion_id, ruta) VALUES (%s, %s)",
                (pub_id, ruta)
            )

    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Publicación creada', 'id': pub_id}), 201


@pub_bp.route('/<int:pub_id>', methods=['DELETE'])
def eliminar(pub_id):
    """Eliminar publicación (solo el dueño o admin)."""
    if 'telefono' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    db = get_db()
    cur = db.connection.cursor()
    cur.execute("SELECT telefono FROM publicaciones WHERE id = %s", (pub_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        return jsonify({'error': 'No encontrada'}), 404

    if row[0] != session['telefono'] and session.get('rol') != 'admin':
        cur.close()
        return jsonify({'error': 'Sin permiso'}), 403

    cur.execute("DELETE FROM publicaciones WHERE id = %s", (pub_id,))
    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Publicación eliminada'})


@pub_bp.route('/categorias', methods=['GET'])
def categorias():
    db = get_db()
    cur = db.connection.cursor()
    cur.execute("SELECT id, nombre FROM categorias")
    rows = cur.fetchall()
    cur.close()
    return jsonify([{'id': r[0], 'nombre': r[1]} for r in rows])



@pub_bp.route('/<int:pub_id>/destacar', methods=['POST'])
def destacar(pub_id):
    """Admin: marcar/desmarcar como destacada. Solo una a la vez."""
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403

    data      = request.get_json()
    activar   = data.get('destacada', True)

    db  = get_db()
    cur = db.connection.cursor()

    if activar:
        # Quitar destacada a todas primero
        cur.execute("UPDATE publicaciones SET destacada = 0")
        cur.execute("UPDATE publicaciones SET destacada = 1 WHERE id = %s", (pub_id,))
    else:
        cur.execute("UPDATE publicaciones SET destacada = 0 WHERE id = %s", (pub_id,))

    db.connection.commit()
    cur.close()
    return jsonify({'mensaje': 'Actualizado'})


@pub_bp.route('/buscar', methods=['GET'])
def buscar():
    """Buscar publicaciones por texto o usuario."""
    q      = request.args.get('q', '').strip()
    limite = int(request.args.get('limite', 20))
    if not q:
        return jsonify([])

    like = f"%{q}%"
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT p.id, p.telefono, p.contenido, p.fecha,
               u.nombre AS autor, u.foto AS autor_foto, u.telefono AS tel_autor,
               p.precio, u.localidad AS comunidad, p.destacada,
               (SELECT COUNT(*) FROM likes l WHERE l.publicacion_id = p.id) AS total_likes,
               (SELECT COUNT(*) FROM comentarios co WHERE co.publicacion_id = p.id) AS total_comentarios
        FROM publicaciones p
        LEFT JOIN usuarios u ON u.telefono = p.telefono
        WHERE p.contenido LIKE %s
           OR u.nombre    LIKE %s
           OR u.telefono  LIKE %s
        ORDER BY p.fecha DESC
        LIMIT %s
    """, (like, like, like, limite))
    rows = cur.fetchall()
    keys = ['id','telefono','contenido','fecha','autor','autor_foto','tel_autor','precio','comunidad','destacada','total_likes','total_comentarios']
    result = []
    for row in rows:
        pub = dict(zip(keys, row))
        pub['fecha'] = str(pub['fecha'])
        cur.execute("SELECT ruta FROM publicaciones_imagenes WHERE publicacion_id = %s", (pub['id'],))
        pub['imagenes'] = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT ruta FROM publicaciones_videos WHERE publicacion_id = %s", (pub['id'],))
        pub['videos'] = [r[0] for r in cur.fetchall()]
        result.append(pub)
    cur.close()
    return jsonify(result)


@pub_bp.route('/admin/lista', methods=['GET'])
def admin_lista():
    """Lista todas las publicaciones para el panel admin."""
    if session.get('rol') != 'admin':
        return jsonify({'error': 'Sin permiso'}), 403
    db  = get_db()
    cur = db.connection.cursor()
    cur.execute("""
        SELECT p.id, p.telefono, p.contenido, p.fecha,
               u.nombre AS autor,
               (SELECT COUNT(*) FROM likes l WHERE l.publicacion_id = p.id) AS likes,
               (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id) AS comentarios
        FROM publicaciones p
        LEFT JOIN usuarios u ON u.telefono = p.telefono
        ORDER BY p.fecha DESC LIMIT 100
    """)
    rows = cur.fetchall()
    keys = ['id','telefono','contenido','fecha','autor','likes','comentarios']
    result = [dict(zip(keys, r)) for r in rows]
    for r in result:
        r['fecha'] = str(r['fecha'])
    cur.close()
    return jsonify(result)
