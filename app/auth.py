import os
import datetime
import jwt
from flask import Blueprint, request, jsonify, session, redirect, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User
from app.utils.oauth import get_google_flow
from googleapiclient.discovery import build
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# --- Tạo JWT Token ---
def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token hết hạn sau 1 giờ
    }
    secret = current_app.config["JWT_SECRET_KEY"]
    return jwt.encode(payload, secret, algorithm="HS256")

# --- Tạo Refresh Token ---
def generate_refresh_token(user_id):
    refresh_payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)  # Refresh token có thời gian sống 7 ngày
    }
    secret = current_app.config["JWT_SECRET_KEY"]
    return jwt.encode(refresh_payload, secret, algorithm="HS256")

# --- Decorator kiểm tra Token ---
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            current_app.logger.error("Token is missing!")
            return jsonify({"message": "Token is missing!"}), 403
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
            if not current_user:
                current_app.logger.error("User not found in database for token!")
                return jsonify({"message": "User not found!"}), 403
        except jwt.ExpiredSignatureError:
            current_app.logger.error("Token has expired!")
            return jsonify({"message": "Token has expired!"}), 403
        except jwt.InvalidTokenError:
            current_app.logger.error("Invalid token!")
            return jsonify({"message": "Invalid token!"}), 403
        except Exception as e:
            current_app.logger.error(f"Error decoding token: {str(e)}")
            return jsonify({"message": f"Token error: {str(e)}"}), 403
        
        return f(current_user, *args, **kwargs)
    return decorated_function

# --- Đăng ký người dùng ---
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    name = data.get("name")

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username đã tồn tại"}), 409

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password=hashed_pw, name=name, role="USER")

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Đăng ký thành công"}), 201

# --- Đăng nhập thường ---
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Tài khoản hoặc mật khẩu không đúng"}), 401

    if user.role == "BANNED":
        return jsonify({"error": "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên."}), 403

    access_token = generate_token(user.id)
    refresh_token = generate_refresh_token(user.id)  # Tạo refresh token

    return jsonify({
        "message": "Đăng nhập thành công",
        "access_token": access_token,
        "refresh_token": refresh_token,  # Gửi refresh token về frontend
        "username": user.username,
        "name": user.name,
        "role": user.role
    }), 200

# --- Đăng nhập bằng Google ---
@auth_bp.route('/login/google')
def login_google():
    flow = get_google_flow()
    auth_url, state = flow.authorization_url(prompt='select_account', access_type='offline')
    session["oauth_state"] = state
    return redirect(auth_url)

# --- Callback sau khi xác thực Google ---
@auth_bp.route("/callback")
def google_callback():
    flow = get_google_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()

    email = user_info.get("email")
    name = user_info.get("name") or email.split("@")[0]

    user = User.query.filter_by(email=email).first()
    is_new = False

    if not user:
        user = User(
            email=email,
            username=email.split("@")[0],
            name=name,
            role="USER",
            oauth_login=True
        )
        db.session.add(user)
        db.session.commit()
        is_new = True
    else:
        user.name = name
        db.session.commit()

    token = generate_token(user.id)

    redirect_uri = (
        f"http://localhost:5173/auth/callback"
        f"?token={token}"
        f"&is_new={str(is_new).lower()}"
        f"&user_id={user.id}"
        f"&username={user.username or ''}"
        f"&name={user.name or ''}"
        f"&email={user.email or ''}"
        f"&role={user.role or ''}"
    )

    current_app.logger.info(f"🔁 REDIRECT URI: {redirect_uri}")
    return redirect(redirect_uri)

# --- Cập nhật profile sau khi đăng nhập Google ---
@auth_bp.route("/update-profile", methods=["POST"])
@token_required  # Bảo vệ route này bằng token
def update_profile(current_user):
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    name = data.get("name")

    user = current_user

    if username and username != user.username:
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({"error": "Username đã tồn tại"}), 409
        user.username = username

    if password:
        user.password = generate_password_hash(password)

    if name:
        user.name = name

    user.oauth_login = False  # Cho phép đăng nhập truyền thống sau khi cập nhật
    db.session.commit()

    return jsonify({"message": "Cập nhật thành công", "user": user.to_dict()}), 200

# --- Cập nhật refresh token ---
@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    refresh_token = request.json.get('refresh_token')
    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400
    
    try:
        data = jwt.decode(refresh_token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
        new_access_token = generate_token(data['user_id'])  # Cấp lại access token
        return jsonify({"access_token": new_access_token}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid refresh token"}), 401
