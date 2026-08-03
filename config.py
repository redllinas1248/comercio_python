import os

class Config:
    MYSQL_HOST     = os.environ.get('MYSQL_HOST',     'sql113.byethost7.com')
    MYSQL_USER     = os.environ.get('MYSQL_USER',     'b7_41480151')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'alan2015')
    MYSQL_DB       = os.environ.get('MYSQL_DB',       'b7_41480151_comercio')
    MYSQL_PORT     = int(os.environ.get('MYSQL_PORT', 3306))

    SECRET_KEY     = os.environ.get('SECRET_KEY', 'comercio-local-2026-xK9mPqL7')

    UPLOAD_FOLDER       = os.path.join('static', 'img', 'posts')
    VIDEO_FOLDER        = os.path.join('static', 'videos', 'posts')
    MAX_CONTENT_LENGTH  = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS  = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_VIDEO_EXTS  = {'mp4', 'mov', 'webm', 'avi'}
