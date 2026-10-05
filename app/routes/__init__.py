from flask import Blueprint

# Đây là blueprint tổng để nhóm các route lại (nếu cần)
routes_bp = Blueprint("routes", __name__)

# Blueprint con từ từng module
from app.routes.courses import courses_bp
from app.routes.public import public_bp
from app.routes.favorites import favorites_bp
from app.routes.history import history_bp

def register_routes(app):
    app.register_blueprint(courses_bp, url_prefix="/api")
    app.register_blueprint(public_bp, url_prefix="/api")
    app.register_blueprint(favorites_bp, url_prefix="/api")
    app.register_blueprint(history_bp, url_prefix="/api")
