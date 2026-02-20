from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField, SelectField, StringField, PasswordField,
    BooleanField, SubmitField, TextAreaField, IntegerField, FloatField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, ValidationError, Optional, NumberRange
)
from wtforms_sqlalchemy.fields import QuerySelectField
from app.models import Deck, User, Category
from flask_login import current_user


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password',
        validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class TaskForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional()])
    due_date = DateTimeLocalField(
        "Due Date",
        format="%Y-%m-%dT%H:%M",
        validators=[Optional()]
    )
    # category = SelectField(
    #     "Category",
    #     choices=[
    #         ("Study", "Study"),
    #         ("Work", "Work"),
    #         ("Personal", "Personal"),
    #         ("Other", "Other")
    #     ],
    #     validators=[DataRequired()]
    # )
    
    category = QuerySelectField(
        'Category',
        query_factory=lambda: Category.query.filter_by(
            user_id=current_user.id,
            deleted_at=None
        ).order_by(Category.name).all(),
        get_label='name',
        allow_blank=True,
        blank_text='-- No Category --'
    )
    other_category = StringField("Other Category", validators=[Optional()])
    submit = SubmitField("Save Task")


class FlashcardForm(FlaskForm):
    question = TextAreaField("Question", validators=[DataRequired()])
    answer = TextAreaField("Answer", validators=[DataRequired()])
    deck = QuerySelectField(
        'Deck',
        query_factory=lambda: Deck.query.filter_by(
            user_id=current_user.id
        ).order_by(Deck.name).all(), # type: ignore
        get_label='name',
        allow_blank=False,
        validators=[DataRequired()]
    )
    submit = SubmitField("Save Flashcard")

class StudyPlanForm(FlaskForm):
    """Form for AI-powered study plan generation"""
    subject = StringField(
        'Subject/Topic',
        validators=[DataRequired()],
        render_kw={"placeholder": "e.g., Calculus, Biology"}
    )
    time_value = IntegerField(
        'Time for the Task',
        validators=[DataRequired(), NumberRange(min=1, max=365)],
        render_kw={"placeholder": "e.g., 14"}
    )
    time_unit = SelectField(
        'Time Unit',
        choices=[
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months')
        ],
        validators=[DataRequired()]
    )
    knowledge_level = SelectField(
        'Knowledge Level',
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced')
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Generate Personalized Plan')

class DeckForm(FlaskForm):
    """Form for creating and editing flashcard decks"""
    name = StringField(
        'Deck Name',
        validators=[DataRequired()],
        render_kw={"placeholder": "e.g., Python Programming, Biology"}
    )
    description = TextAreaField(
        'Description',
        validators=[Optional()],
        render_kw={"placeholder": "What is this deck about?"}
    )
    color = StringField(
        'Color',
        validators=[Optional()],
        render_kw={"type": "color", "value": "#3498db"}
    )
    icon = StringField(
        'Icon (FontAwesome)',
        validators=[Optional()],
        render_kw={"placeholder": "e.g., fa-brain, fa-book, fa-code"}
    )
    submit = SubmitField('Save Deck')