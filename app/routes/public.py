import json
from datetime import datetime
import jwt
from flask import Blueprint, jsonify, request, current_app
from app.models import db, Course, Card, StudyHistory

public_bp = Blueprint("public", __name__)

@public_bp.route("/api/courses/public", methods=["GET"])
def get_public_courses():
    try:
        public_courses = Course.query.filter_by(is_published=True).order_by(Course.id.desc()).all()
        return jsonify([c.to_dict() for c in public_courses])
    except Exception as e:
        current_app.logger.error(f"Error getting public courses: {str(e)}")
        return jsonify({"error": "Failed to load public courses"}), 500

@public_bp.route("/api/public/quiz/<int:course_id>", methods=["GET"])
def get_public_quiz_details(course_id):
    """
    Lấy thông tin chi tiết của một quiz đã xuất bản. Bất kỳ ai cũng có thể truy cập.
    """
    try:
        course = Course.query.filter_by(id=course_id, is_published=True).first_or_404()
        return jsonify(course.to_dict())
    except Exception as e:
        return jsonify({"error": "Quiz not found or not published"}), 404

@public_bp.route("/api/public/quiz/<int:course_id>/questions", methods=["GET"])
def get_public_quiz_questions(course_id):
    """
    Lấy tất cả câu hỏi của một quiz đã xuất bản.
    ĐÃ BẢO VỆ: Loại bỏ đáp án đúng khỏi payload để chống gian lận (inspect element).
    """
    course = Course.query.filter_by(id=course_id, is_published=True).first_or_404()
    cards = Card.query.filter_by(course_id=course.id).all()

    sanitized_cards = []
    for card in cards:
        try:
            back_data = json.loads(card.back or "{}")
        except Exception:
            back_data = {}

        q_type = back_data.get("type", "multipleChoice")
        sanitized_back = {"type": q_type}

        if q_type == "multipleChoice":
            # Chỉ gửi danh sách text của options, KHÔNG gửi thuộc tính 'correct'
            sanitized_back["options"] = [{"text": opt.get("text", "")} for opt in back_data.get("options", [])]
        elif q_type == "fillInTheBlank":
            # Không gửi correctAnswer về phía client
            pass

        sanitized_cards.append({
            "id": card.id,
            "front": card.front,
            "back": json.dumps(sanitized_back),
            "course_id": card.course_id
        })

    return jsonify(sanitized_cards)

@public_bp.route("/api/public/quiz/<int:course_id>/submit", methods=["POST"])
def submit_quiz(course_id):
    """
    Chấm điểm bài thi an toàn trên Server-side.
    """
    course = Course.query.filter_by(id=course_id, is_published=True).first_or_404()
    data = request.get_json() or {}
    user_answers = data.get("answers", {})

    cards = Card.query.filter_by(course_id=course.id).all()
    correct_count = 0
    total = len(cards)
    details = []

    for card in cards:
        user_answer = user_answers.get(str(card.id))
        if user_answer is None:
            user_answer = user_answers.get(card.id, "")

        is_correct = False
        correct_answer_display = ""

        try:
            back_data = json.loads(card.back or "{}")
        except Exception:
            back_data = {}

        q_type = back_data.get("type", "multipleChoice")

        if q_type == "multipleChoice":
            options = back_data.get("options", [])
            correct_opt = next((opt for opt in options if opt.get("correct") is True), None)
            correct_answer_display = correct_opt.get("text", "") if correct_opt else ""
            if correct_opt and str(user_answer).strip() == str(correct_opt.get("text", "")).strip():
                is_correct = True
        elif q_type == "fillInTheBlank":
            actual_answer = back_data.get("correctAnswer", "")
            correct_answer_display = actual_answer
            if str(user_answer).strip().lower() == str(actual_answer).strip().lower():
                is_correct = True

        if is_correct:
            correct_count += 1

        details.append({
            "card_id": card.id,
            "questionText": card.front,
            "userAnswer": user_answer,
            "correctAnswer": correct_answer_display,
            "isCorrect": is_correct
        })

    score_percent = round((correct_count / total * 100)) if total > 0 else 0

    # Nếu người dùng có token đăng nhập thì tự động lưu lịch sử học
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            user_id = payload.get("user_id")
            if user_id:
                history = StudyHistory(user_id=user_id, course_id=course.id, studied_at=datetime.utcnow())
                db.session.add(history)
                db.session.commit()
        except Exception:
            pass

    return jsonify({
        "correctAnswers": correct_count,
        "totalQuestions": total,
        "scorePercent": score_percent,
        "details": details
    })