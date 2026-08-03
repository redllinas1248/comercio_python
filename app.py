from flask import Flask
from config import Config
from db import init_db

app = Flask(__name__)
app.config.from_object(Config)

init_db(app)

# Blueprints API
from routes.auth import auth_bp
from routes.publicaciones import pub_bp
from routes.comentarios import com_bp
from routes.likes import likes_bp
from routes.mensajes import msg_bp
from routes.notificaciones import notif_bp
from routes.directorio import dir_bp

# Blueprints vistas (páginas HTML)
from routes.views import views_bp

app.register_blueprint(auth_bp)
app.register_blueprint(pub_bp)
app.register_blueprint(com_bp)
app.register_blueprint(likes_bp)
app.register_blueprint(msg_bp)
app.register_blueprint(notif_bp)
app.register_blueprint(dir_bp)
app.register_blueprint(views_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
