from flask_mysqldb import MySQL

mysql = MySQL()

def init_db(app):
    mysql.init_app(app)
    with app.app_context():
        cur = mysql.connection.cursor()
        # Tablas de configuración y visitas. Si ya existen, no se modifican.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS visitas (
                id INT(11) NOT NULL AUTO_INCREMENT,
                fecha DATE NOT NULL,
                total INT(11) DEFAULT 1,
                PRIMARY KEY (id),
                UNIQUE KEY fecha_unica (fecha)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INT(11) NOT NULL AUTO_INCREMENT,
                clave VARCHAR(100) NOT NULL,
                valor TEXT,
                PRIMARY KEY (id),
                UNIQUE KEY clave_unica (clave)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        mysql.connection.commit()
        cur.close()

def get_db():
    return mysql
