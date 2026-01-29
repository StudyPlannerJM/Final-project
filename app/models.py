from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))
    
    # Google Calendar Integration Fields
    google_token = db.Column(db.Text, nullable=True)  # Store OAuth token as JSON
    google_calendar_id = db.Column(db.String(255), nullable=True)  # Primary calendar ID
    calendar_sync_enabled = db.Column(db.Boolean, default=False)
    
    tasks = db.relationship('Task', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    data_created = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)   
       
    # category column
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    task_category = db.relationship('Category', backref='tasks', foreign_keys=[category_id])
    
    is_complete = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='todo', nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Google Calendar Integration
    google_event_id = db.Column(db.String(255), nullable=True)  # Link to calendar event
    synced_to_calendar = db.Column(db.Boolean, default=False)
    

    def __repr__(self):
        return (
            f"Task('{self.title}', '{self.due_date}', "
            f"'{self.is_complete}')"
        )


class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship(
        "User", backref=db.backref("flashcards", lazy=True)
    )

    def __repr__(self):
        return (
            f"Flashcard('{self.question}', '{self.answer}', "
            f"'{self.date_created}')"
        )


class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    summary_text = db.Column(db.Text, nullable=True)
    file_type = db.Column(db.String(20), nullable=False)  # 'word', 'pdf', 'ocr'
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship(
        "User", backref=db.backref("summaries", lazy=True)
    )

    def __repr__(self):
        return f"Summary('{self.title}', '{self.date_created}')"

class Category(db.Model):
    """
    Normalized category table - replaces string categories in Task
    Each user has their own set of categories
    """
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#3498db')  # Hex color for UI
    icon = db.Column(db.String(50), nullable=True)  # Icon name or emoji

    # Link to user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Metadata
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete

    # Relationship to user
    owner = db.relationship('User', backref=db.backref('categories', lazy='dynamic'))

    # Ensure each user can't have duplicate category names
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='unique_category_per_user'),
        db.Index('idx_category_user', 'user_id'),
    )

    def __repr__(self):
        return f'<Category {self.name}>'