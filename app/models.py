from flask_login import UserMixin
from datetime import datetime
from app import db  # ✅ import db từ __init__.py

# Model User
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    profile_pic = db.Column(db.String(200))
    password = db.Column(db.String(512))
    role = db.Column(db.String(20), default="USER")
    oauth_login = db.Column(db.Boolean, default=False)
    courses = db.relationship(
        'Course', 
        backref=db.backref('owner', lazy='select'),
        lazy='dynamic',
        cascade="all, delete-orphan"
    )
    favorites = db.relationship("Favorite", backref="user", lazy=True)
    history = db.relationship("StudyHistory", backref="user", lazy=True)

    # === THÊM HÀM NÀY VÀO ===
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            # Lấy danh sách các khóa học của user này
            "courses": [course.to_dict() for course in self.courses]
        }

# Model Course
class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    image = db.Column(db.String(200), nullable=True)  # Cập nhật trường ảnh đại diện
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cards = db.relationship("Card", backref="course", cascade="all, delete-orphan", lazy=True)
    favorites = db.relationship("Favorite", backref="course", lazy=True)
    history = db.relationship("StudyHistory", backref="course", lazy=True)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    def to_dict(self):
        # CHẮC CHẮN RẰNG KHÔNG CÓ favorites hay history ở đây
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "image": self.image,
            "owner_id": self.owner_id,
            "public": self.public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_published": self.is_published,
        }

# Model Card
class Card(db.Model):
    __tablename__ = 'cards'
    id = db.Column(db.Integer, primary_key=True)
    front = db.Column(db.Text)
    back = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    def to_dict(self):
        return {
            "id": self.id,
            "front": self.front,
            "back": self.back,
            "course_id": self.course_id,
    }


# Model Progress
class Progress(db.Model):
    __tablename__ = 'progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    studied = db.Column(db.Integer, default=0)
    correct = db.Column(db.Integer, default=0)

# Model Favorite
class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'course_id', name='_user_course_uc'),)

# Model StudyHistory
class StudyHistory(db.Model):
    __tablename__ = 'study_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    studied_at = db.Column(db.DateTime, default=datetime.utcnow)

