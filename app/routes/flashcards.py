"""
Flashcards Blueprint - Deck and flashcard management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.forms import DeckForm, FlashcardForm
from app.services.deck_service import DeckService
from app.services.flashcard_service import FlashcardService
from app.models import StudyPlan
from app.exceptions import ValidationError, NotFoundError, AuthorizationError

flashcards_bp = Blueprint('flashcards', __name__, url_prefix='/flashcards')


# ==============================================================================
# DECK ROUTES
# ==============================================================================

@flashcards_bp.route('/decks')
@login_required
def decks():
    """Display all decks for the current user"""
    try:
        user_decks = DeckService.get_user_decks(current_user.id)
        # Add flashcard count to each deck
        for deck in user_decks:
            deck.flashcard_count = deck.flashcards.count()
        return render_template("flashcards/decks.html", title="My Decks", decks=user_decks)
    except Exception as e:
        current_app.logger.error(f"Error loading decks: {str(e)}")
        flash("Error loading decks", "danger")
        return redirect(url_for("main.dashboard"))


@flashcards_bp.route("/add_deck", methods=["GET", "POST"])
@login_required
def add_deck():
    """Create a new deck"""
    form = DeckForm()
    if form.validate_on_submit():
        try:
            deck = DeckService.create_deck(
                user_id=current_user.id,
                name=form.name.data,
                description=form.description.data,
                color=form.color.data or '#3498db',
                icon=form.icon.data
            )
            flash(f"Deck '{deck.name}' has been created!", "success")
            return redirect(url_for("flashcards.decks"))
        except ValidationError as e:
            flash(str(e), "danger")
        except Exception as e:
            current_app.logger.error(f"Error creating deck: {str(e)}")
            flash("Error creating deck", "danger")
    
    return render_template("flashcards/add_deck.html", title="Create Deck", form=form)


@flashcards_bp.route("/edit_deck/<int:deck_id>", methods=["GET", "POST"])
@login_required
def edit_deck(deck_id):
    """Edit an existing deck"""
    try:
        deck = DeckService.get_deck_by_id(deck_id, current_user.id)
    except (NotFoundError, AuthorizationError) as e:
        flash(str(e), "danger")
        return redirect(url_for("flashcards.decks"))
    
    form = DeckForm(obj=deck)
    
    if form.validate_on_submit():
        try:
            DeckService.update_deck(
                deck_id=deck_id,
                user_id=current_user.id,
                name=form.name.data,
                description=form.description.data,
                color=form.color.data,
                icon=form.icon.data
            )
            flash(f"Deck '{form.name.data}' has been updated!", "success")
            return redirect(url_for("flashcards.decks"))
        except ValidationError as e:
            flash(str(e), "danger")
        except Exception as e:
            current_app.logger.error(f"Error updating deck: {str(e)}")
            flash("Error updating deck", "danger")
    
    return render_template("flashcards/edit_deck.html", title="Edit Deck", form=form, deck=deck)


@flashcards_bp.route("/delete_deck/<int:deck_id>", methods=["POST"])
@login_required
def delete_deck(deck_id):
    """Delete a deck and all its flashcards"""
    try:
        deck = DeckService.get_deck_by_id(deck_id, current_user.id)
        deck_name = deck.name
        flashcard_count = deck.flashcards.count()
        
        DeckService.delete_deck(deck_id, current_user.id)
        flash(f"Deck '{deck_name}' and {flashcard_count} flashcard(s) have been deleted!", "success")
    except ValidationError as e:
        flash(str(e), "warning")
    except (NotFoundError, AuthorizationError) as e:
        flash(str(e), "danger")
    except Exception as e:
        current_app.logger.error(f"Error deleting deck: {str(e)}")
        flash("Error deleting deck", "danger")
    
    return redirect(url_for("flashcards.decks"))


# ==============================================================================
# FLASHCARD ROUTES
# ==============================================================================

@flashcards_bp.route("/")
@login_required
def index():
    """Display flashcards organized by decks"""
    deck_id = request.args.get('deck_id', type=int)
    
    try:
        # Get all decks for the user
        user_decks = DeckService.get_user_decks(current_user.id)
        
        # Add flashcard count to each deck
        for deck in user_decks:
            deck.flashcard_count = deck.flashcards.count()
        
        # If no deck selected, show deck grid view
        if not deck_id:
            return render_template(
                "flashcards/flashcards.html",
                title="Flashcards",
                decks=user_decks,
                show_decks=True
            )
        
        # If deck selected, show flashcards in that deck
        selected_deck = DeckService.get_deck_by_id(deck_id, current_user.id)
        user_flashcards = FlashcardService.get_user_flashcards(
            current_user.id,
            deck_id=deck_id
        )
        
        return render_template(
            "flashcards/flashcards.html",
            title=f"{selected_deck.name} - Flashcards",
            flashcards=user_flashcards,
            decks=user_decks,
            selected_deck=selected_deck,
            show_decks=False
        )
    except Exception as e:
        current_app.logger.error(f"Error loading flashcards: {str(e)}")
        flash("Error loading flashcards", "danger")
        return redirect(url_for("main.dashboard"))


@flashcards_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Create a new flashcard"""
    form = FlashcardForm()
    
    # Pre-select deck if provided in query parameter
    if request.method == 'GET':
        deck_id = request.args.get('deck_id', type=int)
        if deck_id:
            try:
                deck = DeckService.get_deck_by_id(deck_id, current_user.id)
                form.deck.data = deck
            except Exception:
                pass
    
    if form.validate_on_submit():
        try:
            flashcard = FlashcardService.create_flashcard(
                user_id=current_user.id,
                question=form.question.data,
                answer=form.answer.data,
                deck_id=form.deck.data.id if form.deck.data else None
            )
            flash("Your flashcard has been added!", "success")
            return redirect(url_for("flashcards.index", deck_id=flashcard.deck_id))
        except ValidationError as e:
            flash(str(e), "danger")
        except Exception as e:
            current_app.logger.error(f"Error creating flashcard: {str(e)}")
            flash("Error creating flashcard", "danger")
    
    return render_template("flashcards/add_flashcards.html", title="Add Flashcard", form=form)


@flashcards_bp.route("/edit/<int:flashcard_id>", methods=["GET", "POST"])
@login_required
def edit(flashcard_id):
    """Edit an existing flashcard"""
    try:
        flashcard = FlashcardService.get_flashcard_by_id(flashcard_id, current_user.id)
    except (NotFoundError, AuthorizationError) as e:
        flash(str(e), "danger")
        return redirect(url_for("flashcards.index"))
    
    form = FlashcardForm(obj=flashcard)
    
    # Pre-select the current deck
    if request.method == 'GET':
        form.deck.data = flashcard.deck
    
    if form.validate_on_submit():
        try:
            FlashcardService.update_flashcard(
                flashcard_id=flashcard_id,
                user_id=current_user.id,
                question=form.question.data,
                answer=form.answer.data,
                deck_id=form.deck.data.id if form.deck.data else None
            )
            flash("Your flashcard has been updated!", "success")
            return redirect(url_for("flashcards.index", deck_id=form.deck.data.id))
        except ValidationError as e:
            flash(str(e), "danger")
        except Exception as e:
            current_app.logger.error(f"Error updating flashcard: {str(e)}")
            flash("Error updating flashcard", "danger")
    
    return render_template(
        "flashcards/edit_flashcards.html",
        title="Edit Flashcard",
        form=form,
        flashcard=flashcard
    )


@flashcards_bp.route("/delete/<int:flashcard_id>", methods=["POST"])
@login_required
def delete(flashcard_id):
    """Delete a flashcard"""
    try:
        flashcard = FlashcardService.get_flashcard_by_id(flashcard_id, current_user.id)
        deck_id = flashcard.deck_id
        
        FlashcardService.delete_flashcard(flashcard_id, current_user.id)
        flash("Your flashcard has been deleted!", "success")
        return redirect(url_for("flashcards.index", deck_id=deck_id))
    except (NotFoundError, AuthorizationError) as e:
        flash(str(e), "danger")
    except Exception as e:
        current_app.logger.error(f"Error deleting flashcard: {str(e)}")
        flash("Error deleting flashcard", "danger")
    
    return redirect(url_for("flashcards.index"))


# ==============================================================================
# AI GENERATION ROUTE
# ==============================================================================

@flashcards_bp.route("/generate_from_study_plan/<int:plan_id>", methods=["POST"])
@login_required
def generate_from_study_plan(plan_id):
    """Generate flashcards from a study plan using AI"""
    plan = StudyPlan.query.get_or_404(plan_id)
    
    # Security check
    if plan.user_id != current_user.id:
        flash('You are not authorized to access this plan.', 'danger')
        return redirect(url_for('ai_planner.my_plans'))
    
    # Extract number of cards to generate
    num_cards = int(request.form.get('num_cards', 10))
    
    deck = None  # Initialize to prevent unbound variable error
    try:
        # Auto-create or get deck named after the study plan subject
        deck = DeckService.get_or_create_deck(
            user_id=current_user.id,
            name=plan.subject,
            description=f"Flashcards generated from {plan.subject} study plan",
            color='#9b59b6',  # Purple for AI-generated decks
            icon='fa-robot'
        )
        
        # Use Gemini AI to generate flashcards
        try:
            from google import genai
        except ImportError:
            flash('Google Generative AI library is not installed.', 'danger')
            return redirect(url_for('ai_planner.view_plan', plan_id=plan_id))
        
        # Get API key from config (NEVER hardcode API keys!)
        api_key = current_app.config.get('GEMINI_API_KEY')
        if not api_key:
            flash('Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.', 'danger')
            return redirect(url_for('ai_planner.view_plan', plan_id=plan_id))
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Based on the following study plan for {plan.subject}, generate {num_cards} flashcards 
to help the student review key concepts. Each flashcard should have a clear question and a concise answer.

Study Plan:
{plan.plan_content}

Generate exactly {num_cards} flashcards in the following format:
Q: [Question]
A: [Answer]

Make the questions specific and the answers clear and educational."""
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        
        # Parse Q&A pairs
        flashcard_text = response.text or ""
        lines = flashcard_text.strip().split('\n')
        
        flashcards_data = []
        question = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('Q:'):
                question = line[2:].strip()
            elif line.startswith('A:') and question:
                answer = line[2:].strip()
                flashcards_data.append({
                    'question': question,
                    'answer': answer
                })
                question = None
        
        # Use service to bulk create flashcards
        created_flashcards = FlashcardService.bulk_create_flashcards(
            user_id=current_user.id,
            flashcards_data=flashcards_data,
            deck_id=deck.id
        )
        
        flash(
            f"Successfully generated {len(created_flashcards)} flashcards in deck '{deck.name}'!",
            'success'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating flashcards: {str(e)}")
        flash(f'Error generating flashcards: {str(e)}', 'danger')
    
    # Redirect to deck page or ai_planner if deck wasn't created
    if deck:
        return redirect(url_for('flashcards.index', deck_id=deck.id))
    else:
        return redirect(url_for('ai_planner.view_plan', plan_id=plan_id))
