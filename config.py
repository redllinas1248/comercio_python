import os
import cloudinary

class Config:
    MYSQL_HOST     = os.environ.get('MYSQL_HOST',     'sql3.freesqldatabase.com')
    MYSQL_USER     = os.environ.get('MYSQL_USER',     'sql3834541')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'qUDfkjI1SB')
    MYSQL_DB       = os.environ.get('MYSQL_DB',       'sql3834541')
    MYSQL_PORT     = int(os.environ.get('MYSQL_PORT', 3306))

    SECRET_KEY = os.environ.get('SECRET_KEY', 'comercio-azueta-2026-seguro')

    UPLOAD_FOLDER      = os.path.join('static', 'img', 'posts')
    VIDEO_FOLDER       = os.path.join('static', 'videos', 'posts')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_VIDEO_EXTS = {'mp4', 'mov', 'webm', 'avi'}

    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', 'llinas')
    CLOUDINARY_API_KEY    = os.environ.get('CLOUDINARY_API_KEY',    '637691336519819')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '1_FqsCD1JXh_oraFq__5_xCO7-E')


def init_cloudinary(app):
    cloudinary.config(
        cloud_name = app.config['CLOUDINARY_CLOUD_NAME'],
        api_key    = app.config['CLOUDINARY_API_KEY'],
        api_secret = app.config['CLOUDINARY_API_SECRET'],
        secure     = True
    )
