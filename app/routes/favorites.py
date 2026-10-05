from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.models import db, Course, Favorite

favorites_bp = Blueprint("favorites", __name__)

# Thêm course vào danh sách yêu thích
@favorites_bp.route("/favorites", methods=["POST"])
def add_favorite():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json or {}
    course_id = data.get("course_id")

    if not course_id:
        return jsonify({"error": "Missing course_id"}), 400

    course = Course.query.get(course_id)
    if not course or (not course.public and course.owner_id != current_user.id):
        return jsonify({"error": "Course not found or not accessible"}), 404

    existing = Favorite.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if existing:
        return jsonify({"message": "Course already in favorites"}), 200

    fav = Favorite(user_id=current_user.id, course_id=course_id)
    db.session.add(fav)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500

    return jsonify({"message": "Added to favorites"})

# Bỏ course khỏi danh sách yêu thích
@favorites_bp.route("/favorites/<int:course_id>", methods=["DELETE"])
def remove_favorite(course_id):
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401

    fav = Favorite.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not fav:
        return jsonify({"error": "Favorite not found"}), 404

    db.session.delete(fav)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500

    return jsonify({"message": "Removed from favorites"})

# Lấy danh sách course đã yêu thích
@favorites_bp.route("/favorites", methods=["GET"])
def get_favorites():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401

    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    course_list = []

    for f in favorites:
        course = Course.query.get(f.course_id)
        if course:
            course_list.append({
                "id": course.id,
                "name": course.name,
                "public": course.public,
                "owner_id": course.owner_id
            })

    return jsonify(course_list)
