# type: ignore
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash
)
from app.models import Task, Flashcard
from app import db
from flask_login import login_required, current_user
from app.forms import TaskForm, FlashcardForm

main = Blueprint('main', __name__)


@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.data_created.asc()
    ).all()
    return render_template(
        'dashboard.html', title='Dashboard', tasks=tasks
    )


@main.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    form = TaskForm()  # Initialize form
    if form.validate_on_submit():
        category = form.category.data
        if category == "Other" and form.other_category.data.strip():
            category = form.other_category.data.strip()

        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            category=category,
            author=current_user
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task added successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('add_task.html', title='Add New Task', form=form)


@main.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:  # Simple authorization check
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = TaskForm(obj=task)

    if request.method == "GET":
        default_choices = [c[0] for c in form.category.choices]
        if task.category not in default_choices:
            form.category.data = "Other"
            form.other_category.data = task.category

    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data

        category = form.category.data
        if category == "Other" and form.other_category.data.strip():
            category = form.other_category.data.strip()
        task.category = category

        db.session.commit()
        flash("Your task has been updated!", "success")
        return redirect(url_for("main.dashboard"))
    return render_template(
        "edit_task.html", title="Edit Task", form=form, task=task
    )


@main.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:  # Simple authorization check
        flash('You are not authorized to delete this task.', 'danger')
        return redirect(url_for('main.dashboard'))

    db.session.delete(task)
    db.session.commit()
    flash('Your task has been deleted!', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:  # Simple authorization check
        flash('You are not authorized to complete this task.', 'danger')
        return redirect(url_for('main.dashboard'))
    task.is_complete = not task.is_complete
    db.session.commit()
    flash('Task status updated!', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html', title='Settings')


@main.route("/pomodoro")
@login_required
def pomodoro():
    return render_template("pomodoro.html", title="Pomodoro Timer")


@main.route("/flashcards")
@login_required
def flashcards():
    user_flashcards = Flashcard.query.filter_by(
        author=current_user
    ).order_by(Flashcard.date_created.desc()).all()
    return render_template(
        "flashcards.html", title="Flashcards", flashcards=user_flashcards
    )


@main.route("/add_flashcard", methods=["GET", "POST"])
@login_required
def add_flashcard():
    form = FlashcardForm()
    if form.validate_on_submit():
        new_flashcard = Flashcard(
            question=form.question.data,
            answer=form.answer.data,
            author=current_user
        )
        db.session.add(new_flashcard)
        db.session.commit()
        flash("Your flashcard has been added!", "success")
        return redirect(url_for("main.flashcards"))
    return render_template(
        "add_flashcards.html", title="Add Flashcard", form=form
    )


@main.route("/edit_flashcard/<int:flashcard_id>", methods=["GET", "POST"])
@login_required
def edit_flashcard(flashcard_id):
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    if flashcard.author != current_user:
        flash("You are not authorized to edit this flashcard.", "danger")
        return redirect(url_for("main.flashcards"))

    form = FlashcardForm(obj=flashcard)  # Pre-populate form
    if form.validate_on_submit():
        flashcard.question = form.question.data
        flashcard.answer = form.answer.data
        db.session.commit()
        flash("Your flashcard has been updated!", "success")
        return redirect(url_for("main.flashcards"))
    return render_template(
        "edit_flashcards.html",
        title="Edit Flashcard",
        form=form,
        flashcard=flashcard
    )


@main.route("/delete_flashcard/<int:flashcard_id>", methods=["POST"])
@login_required
def delete_flashcard(flashcard_id):
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    if flashcard.author != current_user:
        flash("You are not authorized to delete this flashcard.", "danger")
        return redirect(url_for("main.flashcards"))

    db.session.delete(flashcard)
    db.session.commit()
    flash("Your flashcard has been deleted!", "success")
    return redirect(url_for("main.flashcards"))
