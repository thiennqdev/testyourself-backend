import os
import json # Import json để xử lý dữ liệu options
import uuid
from flask import Blueprint, request, jsonify, current_app
from app.models import db, Course, Card
from app.auth import token_required
from werkzeug.utils import secure_filename

courses_bp = Blueprint("courses", __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_image(image_file, upload_folder):
    if not image_file or not image_file.filename:
        return None
    if not allowed_file(image_file.filename):
        raise ValueError("Invalid file format. Only png, jpg, jpeg, gif, webp are allowed.")
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    ext = image_file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    image_path = os.path.join(upload_folder, unique_filename)
    image_file.save(image_path)
    return f"uploads/{unique_filename}"

# --- ROUTES CHO KHÓA HỌC (COURSES) ---

@courses_bp.route("/api/courses", methods=["POST"])
@token_required
def create_course(current_user):
    try:
        if 'name' not in request.form:
            return jsonify({"error": "Course name is required"}), 400

        name = request.form.get("name")
        description = request.form.get("description", "")
        image = request.files.get("image")
        image_url = None

        if image:
            try:
                image_url = save_uploaded_image(image, current_app.config['UPLOAD_FOLDER'])
            except ValueError as ve:
                return jsonify({"error": str(ve)}), 400

        new_course = Course(
            name=name, 
            description=description, 
            image=image_url, 
            owner_id=current_user.id
        )
        db.session.add(new_course)
        db.session.commit()

        return jsonify({"message": "Course created successfully", "course": new_course.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating course: {str(e)}")
        return jsonify({"error": "An error occurred while creating the course"}), 500

@courses_bp.route("/api/courses", methods=["GET"])
@token_required
def get_courses(current_user):
    try:
        # ĐÂY LÀ DÒNG ĐÚNG: Lọc theo owner_id của người dùng hiện tại
        courses = Course.query.filter_by(owner_id=current_user.id).order_by(Course.id.desc()).all()
        print(f"--- MY COURSES DEBUG: Found {len(courses)} courses for user {current_user.id}. ---")
        return jsonify([c.to_dict() for c in courses])
    except Exception as e:
        current_app.logger.error(f"Error getting courses for user {current_user.id}: {str(e)}")
        return jsonify({"error": "Failed to load your courses"}), 500

@courses_bp.route("/api/courses/<int:course_id>", methods=["GET"])
@token_required
def get_course(current_user, course_id):
    course = None
    # Nếu là admin thì không cần kiểm tra owner_id
    if current_user.role == "ADMIN":
        course = Course.query.get_or_404(course_id)
    else:
        # User thường chỉ được xem course của mình
        course = Course.query.filter_by(id=course_id, owner_id=current_user.id).first_or_404()
    
    # --- PHẦN SỬA ĐỔI NẰM Ở ĐÂY ---
    # Lấy dữ liệu của course dưới dạng dictionary
    course_data = course.to_dict() 
    
    # Lấy tất cả các card (câu hỏi) thuộc về course này
    cards = Card.query.filter_by(course_id=course.id).all()
    
    # Thêm danh sách các card đã được chuyển thành dictionary vào course_data
    course_data['cards'] = [card.to_dict() for card in cards]
    
    # Trả về object JSON hoàn chỉnh
    return jsonify(course_data)

@courses_bp.route("/api/courses/<int:course_id>", methods=["PUT"])
@token_required
def update_course(current_user, course_id):
    course = Course.query.filter_by(id=course_id, owner_id=current_user.id).first_or_404()
    
    try:
        name = request.form.get("name")
        description = request.form.get("description")
        image = request.files.get("image")

        if name:
            course.name = name
        if description is not None:
            course.description = description
        
        if image:
            try:
                new_image_url = save_uploaded_image(image, current_app.config['UPLOAD_FOLDER'])
                if course.image:
                    old_filename = os.path.basename(course.image)
                    old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_filename)
                    if os.path.exists(old_image_path):
                        try:
                            os.remove(old_image_path)
                        except OSError:
                            pass
                course.image = new_image_url
            except ValueError as ve:
                return jsonify({"error": str(ve)}), 400

        db.session.commit()
        return jsonify({"message": "Course updated successfully", "course": course.to_dict()})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating course {course_id}: {str(e)}")
        return jsonify({"error": "An error occurred while updating the course"}), 500


@courses_bp.route("/api/courses/<int:course_id>", methods=["DELETE"])
@token_required
def delete_course(current_user, course_id):
    course = Course.query.filter_by(id=course_id, owner_id=current_user.id).first_or_404()
    try:
        Card.query.filter_by(course_id=course.id).delete()
        db.session.delete(course)
        db.session.commit()
        return jsonify({"message": "Course deleted successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting course {course_id}: {str(e)}")
        return jsonify({"error": "Database error while deleting course"}), 500


# --- ROUTES CHO CÂU HỎI (CARDS) TRONG MỘT KHÓA HỌC ---
@courses_bp.route("/api/courses/<int:course_id>/cards", methods=["POST"])
@token_required
def add_card_to_course(current_user, course_id):
    course = Course.query.filter_by(id=course_id, owner_id=current_user.id).first_or_404()
    data = request.json or {}
    
    question_text = data.get("questionText")
    question_type = data.get("type")

    if not question_text or not question_type:
        return jsonify({"error": "Question text and type are required"}), 400

    # Xây dựng nội dung cho trường 'back' dựa trên loại câu hỏi
    back_content_data = {"type": question_type}
    if question_type == 'multipleChoice':
        back_content_data['options'] = data.get("options", [])
    elif question_type == 'fillInTheBlank':
        back_content_data['correctAnswer'] = data.get("correctAnswer", "")
    
    # Chuyển toàn bộ object thành một chuỗi JSON để lưu
    back_content_json = json.dumps(back_content_data)
    
    new_card = Card(
        front=question_text, 
        back=back_content_json, # Lưu chuỗi JSON vào trường back
        course_id=course.id
    )
    
    try:
        db.session.add(new_card)
        db.session.commit()
        return jsonify({"message": "Card added successfully", "card": new_card.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding card to course {course_id}: {str(e)}")
        return jsonify({"error": "Database error while adding card"}), 500


@courses_bp.route("/api/courses/<int:course_id>/cards", methods=["GET"])
@token_required
def get_cards_for_course(current_user, course_id):
    course = Course.query.filter_by(id=course_id, owner_id=current_user.id).first_or_404()
    cards = Card.query.filter_by(course_id=course.id).all()
    return jsonify([card.to_dict() for card in cards])

@courses_bp.route("/api/courses/<int:course_id>/publish", methods=["POST"])
@token_required
def publish_course_quiz(current_user, course_id):
    course = Course.query.filter_by(id=course_id, owner_id=current_user.id).first_or_404()
    
    # Lấy danh sách câu hỏi từ frontend gửi lên
    data = request.json or {}
    questions_data = data.get("questions", [])

    if not questions_data:
        return jsonify({"error": "Cannot publish a quiz with no questions"}), 400

    try:
        # Xóa các câu hỏi (cards) cũ của khóa học này để tránh trùng lặp
        Card.query.filter_by(course_id=course.id).delete()

        # Thêm lại toàn bộ danh sách câu hỏi mới
        for q_data in questions_data:
            question_text = q_data.get("questionText")
            back_content_data = {
                "type": q_data.get("type"),
                "options": q_data.get("options", []),
                "correctAnswer": q_data.get("correctAnswer", "")
            }
            back_content_json = json.dumps(back_content_data)

            new_card = Card(
                front=question_text, 
                back=back_content_json,
                course_id=course.id
            )
            db.session.add(new_card)

        # Đánh dấu khóa học là đã xuất bản
        course.is_published = True
        
        db.session.commit()
        return jsonify({"message": "Quiz published successfully!"})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error publishing quiz {course_id}: {str(e)}")
        return jsonify({"error": "An error occurred while publishing the quiz"}), 500
    
# Cho phép admin cập nhật course bất kỳ (không cần là owner)
@courses_bp.route("/api/admin/courses/<int:course_id>", methods=["PUT"])
@token_required
def admin_update_course(current_user, course_id):
    if current_user.role != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    course = Course.query.get_or_404(course_id)
    try:
        name = request.form.get("name")
        description = request.form.get("description")
        image = request.files.get("image")

        if name:
            course.name = name
        if description is not None:
            course.description = description

        if image:
            try:
                new_image_url = save_uploaded_image(image, current_app.config['UPLOAD_FOLDER'])
                if course.image:
                    old_filename = os.path.basename(course.image)
                    old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_filename)
                    if os.path.exists(old_image_path):
                        try:
                            os.remove(old_image_path)
                        except OSError:
                            pass
                course.image = new_image_url
            except ValueError as ve:
                return jsonify({"error": str(ve)}), 400

        db.session.commit()
        return jsonify({"message": "Course updated successfully", "course": course.to_dict()})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Admin update course error: {str(e)}")
        return jsonify({"error": "Failed to update course"}), 500
