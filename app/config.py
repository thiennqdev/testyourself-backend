import os
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

# Khai báo basedir trước khi sử dụng nó
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt_dev_secret")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    # Cấu hình thư mục lưu trữ ảnh & giới hạn upload
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(basedir, 'uploads'))  # Đường dẫn đến thư mục uploads
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}  # Các định dạng ảnh cho phép
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # Tối đa 5MB

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URL") or \
        'mysql+pymysql://root:your_mysql_password@localhost/testyourself_db'

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL") or 'sqlite:///:memory:'  # Cấu hình cho database test
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = "placeholder"  # Gán tạm giá trị tránh lỗi nếu không có DATABASE_URL

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
