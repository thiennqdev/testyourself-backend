# app/admin.py

from flask import Blueprint, jsonify, request
from app.models import db, User, Course
from app.auth import token_required  # middleware JWT

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# DASHBOARD
@admin_bp.route("/dashboard-data", methods=["GET"])
@token_required
def get_dashboard_data(current_user):
    if current_user.role != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403

    all_users = User.query.all()
    all_courses = Course.query.all()

    users_list = [user.to_dict() for user in all_users]
    courses_list = [course.to_dict() for course in all_courses]

    return jsonify({
        "users": users_list,
        "courses": courses_list
    })

# GET USERS
@admin_bp.route("/users", methods=["GET"])
@token_required
def get_users(current_user):
    if current_user.role != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403

    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

# BAN / UNBAN USER
@admin_bp.route("/users/<int:user_id>/ban", methods=["PUT"])
@token_required
def toggle_user_ban(current_user, user_id):
    if current_user.role != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.role == "ADMIN":
        return jsonify({"error": "Cannot ban admin"}), 403

    user.role = "BANNED" if user.role != "BANNED" else "USER"
    db.session.commit()
    return jsonify({"message": f"User role set to {user.role}"})

# DELETE COURSE
@admin_bp.route("/flashcards/<int:course_id>", methods=["DELETE"])
@token_required
def delete_course_by_admin(current_user, course_id):
    if current_user.role != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    db.session.delete(course)
    db.session.commit()
    return jsonify({"message": "Course deleted by admin"})

@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@token_required
def update_user_by_admin(current_user, user_id):
    if current_user.role != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403
    
    user_to_update = User.query.get(user_id)
    if not user_to_update:
        return jsonify({"error": "User not found"}), 404
        
    # Không cho phép thay đổi thông tin của Admin khác
    # (Cho phép tự sửa thông tin của chính mình)
    if user_to_update.role == "ADMIN" and user_to_update.id != current_user.id:
        return jsonify({"error": "Cannot modify another admin's data"}), 403

    # --- SỬA LỖI Ở ĐÂY ---
    data = request.get_json()
    # Kiểm tra xem client có gửi JSON hợp lệ không
    if not data:
        return jsonify({"error": "Invalid request. Missing JSON body."}), 400

    name = data.get("name")
    role = data.get("role")

    # Cập nhật tên nếu có
    if name is not None:  # Kiểm tra cả trường hợp name là chuỗi rỗng
        user_to_update.name = name

    # Chỉ cho phép thay đổi vai trò nếu người dùng không phải là Admin
    if role and user_to_update.role != "ADMIN":
        if role in ["USER", "BANNED"]: # Các vai trò được phép
             user_to_update.role = role
        else:
            return jsonify({"error": "Invalid role specified"}), 400

    try:
        db.session.commit()
        # Làm mới đối tượng user sau khi commit để đảm bảo dữ liệu là mới nhất
        db.session.refresh(user_to_update)
        return jsonify({
            "message": "User updated successfully", 
            "user": user_to_update.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        # Ghi lại log lỗi để debug
        current_app.logger.error(f"Failed to update user {user_id}: {str(e)}")
        return jsonify({"error": "Database error occurred."}), 500


# DELETE USER
@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@token_required
def delete_user_by_admin(current_user, user_id):
    if current_user.role != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403
        
    if current_user.id == user_id:
        return jsonify({"error": "You cannot delete yourself"}), 403

    user_to_delete = User.query.get(user_id)
    if not user_to_delete:
        return jsonify({"error": "User not found"}), 404
        
    if user_to_delete.role == "ADMIN":
        return jsonify({"error": "Cannot delete an admin account"}), 403

    db.session.delete(user_to_delete)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"})