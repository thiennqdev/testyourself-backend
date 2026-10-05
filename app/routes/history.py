from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.models import db, Course, StudyHistory
from datetime import datetime

history_bp = Blueprint("history", __name__)

# Ghi lại lịch sử học
@history_bp.route("/history", methods=["POST"])
def record_history():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json or {}
    course_id = data.get("course_id")

    if not course_id:
        return jsonify({"error": "Missing course_id"}), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    history = StudyHistory(user_id=current_user.id, course_id=course.id, studied_at=datetime.utcnow())
    db.session.add(history)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500

    return jsonify({"message": "Study history recorded"})

# Lấy danh sách lịch sử học
@history_bp.route("/history", methods=["GET"])
def get_history():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401

    history = StudyHistory.query.filter_by(user_id=current_user.id).order_by(StudyHistory.studied_at.desc()).all()

    result = []
    for h in history:
        course = Course.query.get(h.course_id)
        if course:
            result.append({
                "course_id": course.id,
                "course_name": course.name,
                "studied_at": h.studied_at.isoformat()
            })

    return jsonify(result)
