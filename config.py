import os
import cloudinary

class Config:
    MYSQL_HOST     = os.environ.get('MYSQL_HOST')
    MYSQL_USER     = os.environ.get('MYSQL_USER')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
    MYSQL_DB       = os.environ.get('MYSQL_DB')
    MYSQL_PORT     = int(os.environ.get('MYSQL_PORT', 3306))

    # Soporte completo de emojis y caracteres especiales
    MYSQL_CHARSET  = 'utf8mb4'

    SECRET_KEY = os.environ.get('SECRET_KEY')

    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30

    UPLOAD_FOLDER      = os.path.join('static', 'img', 'posts')
    VIDEO_FOLDER       = os.path.join('static', 'videos', 'posts')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_VIDEO_EXTS = {'mp4', 'mov', 'webm', 'avi'}

    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY    = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')


def init_cloudinary(app):
    cloudinary.config(
        cloud_name = app.config['CLOUDINARY_CLOUD_NAME'],
        api_key    = app.config['CLOUDINARY_API_KEY'],
        api_secret = app.config['CLOUDINARY_API_SECRET'],
        secure     = True
    )
