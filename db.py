from flask_mysqldb import MySQL

mysql = MySQL()

def init_db(app):
    mysql.init_app(app)

def get_db():
    return mysql
