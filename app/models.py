from app import db
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event


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
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.DateTime, nullable=True)   
       
    # Category column
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    task_category = db.relationship('Category', backref='tasks', foreign_keys=[category_id])
    
    is_complete = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='todo', nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Pomodoro Session
    actual_minutes = db.Column(db.Integer, default=0)  # Auto-calculated from sessions
    
    # Google Calendar Integration
    google_event_id = db.Column(db.String(255), nullable=True)  # Link to calendar event
    synced_to_calendar = db.Column(db.Boolean, default=False)
    
    def __init__(self, title, user_id, description=None, due_date=None, category_id=None, **kwargs):
        """Initialize a task with required and optional parameters"""
        super().__init__(**kwargs)
        self.title = title
        self.user_id = user_id
        self.description = description
        self.due_date = due_date
        self.category_id = category_id

    def __repr__(self):
        return (
            f"Task('{self.title}', '{self.due_date}', "
            f"'{self.is_complete}')"
        )


class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('deck.id'), nullable=True)
    
    author = db.relationship(
        "User", backref=db.backref("flashcards", lazy=True)
    )

    def __init__(self, question, answer, user_id, deck_id=None, **kwargs):
        """Initialize a flashcard with question, answer, user_id, and optional deck_id"""
        super().__init__(**kwargs)
        self.question = question
        self.answer = answer
        self.user_id = user_id
        self.deck_id = deck_id

    def __repr__(self):
        return (
            f"Flashcard('{self.question}', '{self.answer}', "
            f"'{self.date_created}')"
        )

class Deck(db.Model):
    """
    Deck model for organizing flashcards
    Each user can have multiple decks to organize their flashcards
    """
    __tablename__ = 'deck'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#3498db')  # Hex color for UI
    icon = db.Column(db.String(50), nullable=True)  # FontAwesome icon name
    
    # Link to user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Metadata
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    owner = db.relationship('User', backref=db.backref('decks', lazy='dynamic'))
    flashcards = db.relationship('Flashcard', backref='deck', lazy='dynamic', cascade='all, delete-orphan')
    
    # Ensure each user can't have duplicate deck names
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='unique_deck_per_user'),
        db.Index('idx_deck_user', 'user_id'),
    )
    
    def __init__(self, name, user_id, description=None, color='#3498db', icon=None, is_default=False, **kwargs):
        """Initialize a deck with name, user_id, and optional parameters"""
        super().__init__(**kwargs)
        self.name = name
        self.user_id = user_id
        self.description = description
        self.color = color
        self.icon = icon
        self.is_default = is_default
    
    def __repr__(self):
        return f'<Deck {self.name}>'

class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    summary_text = db.Column(db.Text, nullable=True)
    file_type = db.Column(db.String(20), nullable=False)  # 'word', 'pdf', 'ocr'
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship(
        "User", backref=db.backref("summaries", lazy=True)
    )

    def __init__(self, title, original_filename, file_type, user_id, extracted_text=None, summary_text=None, **kwargs):
        """Initialize a summary with required and optional parameters"""
        super().__init__(**kwargs)
        self.title = title
        self.original_filename = original_filename
        self.file_type = file_type
        self.user_id = user_id
        self.extracted_text = extracted_text
        self.summary_text = summary_text

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete

    # Relationship to user
    owner = db.relationship('User', backref=db.backref('categories', lazy='dynamic'))

    # Ensure each user can't have duplicate category names
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='unique_category_per_user'),
        db.Index('idx_category_user', 'user_id'),
    )

    def __init__(self, name, user_id, description=None, color='#3498db', icon=None, is_default=False, **kwargs):
        """Initialize a category with required and optional parameters"""
        super().__init__(**kwargs)
        self.name = name
        self.user_id = user_id
        self.description = description
        self.color = color
        self.icon = icon
        self.is_default = is_default

    def __repr__(self):
        return f'<Category {self.name}>'


class StudyPlan(db.Model):
    """Model for storing AI-generated study plans"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Input parameters
    subject = db.Column(db.String(200), nullable=False)
    time_value = db.Column(db.Integer, nullable=False)
    time_unit = db.Column(db.String(20), nullable=False)  # 'days', 'weeks', or 'months'
    knowledge_level = db.Column(db.String(50), nullable=False)
    
    # Generated plan content
    plan_content = db.Column(db.Text, nullable=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = db.relationship('User', backref=db.backref('study_plans', lazy='dynamic'))
    
    def __init__(self, user_id, subject, time_value, time_unit, knowledge_level, plan_content, **kwargs):
        """Initialize a study plan with required parameters"""
        super().__init__(**kwargs)
        self.user_id = user_id
        self.subject = subject
        self.time_value = time_value
        self.time_unit = time_unit
        self.knowledge_level = knowledge_level
        self.plan_content = plan_content
    
    def __repr__(self):
        return f'<StudyPlan {self.subject} for {self.user_id}>'
    

class StudySession(db.Model):
    """
    Tracks study time spent on tasks
    Can be created manually or automatically from PomodoroSession
    """
    __tablename__ = 'study_session'

    id = db.Column(db.Integer, primary_key=True)

    # Time tracking
    start_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)  # Calculated on end

    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)

    # Optional details
    notes = db.Column(db.Text, nullable=True)
    productivity_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', backref=db.backref('study_sessions', lazy='dynamic'))
    task = db.relationship('Task', backref=db.backref('study_sessions', lazy='dynamic'))

    def __init__(self, user_id, start_time, end_time=None, duration_minutes=None, task_id=None, notes=None, productivity_rating=None, **kwargs):
        """Initialize a study session with required and optional parameters"""
        super().__init__(**kwargs)
        self.user_id = user_id
        self.start_time = start_time
        self.end_time = end_time
        self.duration_minutes = duration_minutes
        self.task_id = task_id
        self.notes = notes
        self.productivity_rating = productivity_rating

    def calculate_duration(self):
        """Calculate duration in minutes"""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)

    def __repr__(self):
        return f'<StudySession {self.id}: {self.duration_minutes}min>'


class PomodoroSession(db.Model):
    """
    Tracks individual Pomodoro timer sessions
    Each session can link to a StudySession
    """
    __tablename__ = 'pomodoro_session'

    id = db.Column(db.Integer, primary_key=True)

    # Session details
    duration_minutes = db.Column(db.Integer, default=25)
    break_duration_minutes = db.Column(db.Integer, default=5)

    # Time
    start_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)  # Did user finish or abandon?

    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    study_session_id = db.Column(db.Integer, db.ForeignKey('study_session.id'), nullable=True)

    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', backref=db.backref('pomodoro_sessions', lazy='dynamic'))
    task = db.relationship('Task', backref=db.backref('pomodoro_sessions', lazy='dynamic'))
    study_session = db.relationship('StudySession', backref=db.backref('pomodoro_session', uselist=False))

    def __init__(self, user_id, start_time, duration_minutes=25, break_duration_minutes=5, end_time=None, completed=False, task_id=None, study_session_id=None, notes=None, **kwargs):
        """Initialize a pomodoro session with required and optional parameters"""
        super().__init__(**kwargs)
        self.user_id = user_id
        self.start_time = start_time
        self.duration_minutes = duration_minutes
        self.break_duration_minutes = break_duration_minutes
        self.end_time = end_time
        self.completed = completed
        self.task_id = task_id
        self.study_session_id = study_session_id
        self.notes = notes

    def __repr__(self):
        return f'<PomodoroSession {self.id}: {self.duration_minutes}min>'
