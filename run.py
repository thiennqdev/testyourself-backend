# run.py
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()

from app import create_app
from app.models import db
from flask_migrate import Migrate

# Lấy cấu hình ứng dụng (mặc định là 'development')
config_name = os.getenv('FLASK_CONFIG', 'development')
app = create_app(config_name)

# Khởi tạo Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    # BẬT DEBUG luôn (không phụ thuộc config file)
    app.run(debug=True)
