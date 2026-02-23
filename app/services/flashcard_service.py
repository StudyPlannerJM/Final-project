"""
Flashcard service for business logic related to flashcards
"""

from app import db
from app.models import Flashcard, Deck, User
from app.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)
from app.services.deck_service import DeckService


class FlashcardService:
    """Service class for flashcard operations"""
    
    @staticmethod
    def create_flashcard(user_id, question, answer, deck_id=None):
        """
        Create a new flashcard with validation.
        
        Args:
            user_id: ID of the user creating the flashcard
            question: Question text
            answer: Answer text
            deck_id: Optional deck ID (uses default deck if not provided)
            
        Returns:
            Created Flashcard object
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If user or deck not found
            AuthorizationError: If user doesn't own the deck
        """
        # Validate question
        if not question or len(question.strip()) < 1:
            raise ValidationError("Question is required")
        
        # Validate answer
        if not answer or len(answer.strip()) < 1:
            raise ValidationError("Answer is required")
        
        # Validate user exists
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        # Handle deck assignment
        if deck_id:
            # Validate deck exists and user owns it
            deck = DeckService.get_deck_by_id(deck_id, user_id)
        else:
            # Use default deck
            deck = DeckService.get_default_deck(user_id)
            deck_id = deck.id
        
        # Create flashcard
        flashcard = Flashcard(
            question=question.strip(),
            answer=answer.strip(),
            user_id=user_id,
            deck_id=deck_id
        )
        
        db.session.add(flashcard)
        db.session.commit()
        
        return flashcard
    
    @staticmethod
    def get_flashcard_by_id(flashcard_id, user_id):
        """
        Get a specific flashcard by ID with authorization check.
        
        Args:
            flashcard_id: ID of the flashcard
            user_id: ID of the user requesting the flashcard
            
        Returns:
            Flashcard object
            
        Raises:
            NotFoundError: If flashcard not found
            AuthorizationError: If user doesn't own the flashcard
        """
        flashcard = db.session.get(Flashcard, flashcard_id)
        
        if not flashcard:
            raise NotFoundError(f"Flashcard with id {flashcard_id} not found")
        
        if flashcard.user_id != user_id:
            raise AuthorizationError(
                "You are not authorized to access this flashcard"
            )
        
        return flashcard
    
    @staticmethod
    def update_flashcard(flashcard_id, user_id, question=None, answer=None, deck_id=None):
        """
        Update a flashcard's properties.
        
        Args:
            flashcard_id: ID of the flashcard to update
            user_id: ID of the user making the update
            question: Optional new question
            answer: Optional new answer
            deck_id: Optional new deck ID
            
        Returns:
            Updated Flashcard object
            
        Raises:
            NotFoundError: If flashcard or deck not found
            AuthorizationError: If user doesn't own the flashcard or deck
            ValidationError: If validation fails
        """
        flashcard = FlashcardService.get_flashcard_by_id(flashcard_id, user_id)
        
        # Update question if provided
        if question is not None:
            if not question or len(question.strip()) < 1:
                raise ValidationError("Question is required")
            flashcard.question = question.strip()
        
        # Update answer if provided
        if answer is not None:
            if not answer or len(answer.strip()) < 1:
                raise ValidationError("Answer is required")
            flashcard.answer = answer.strip()
        
        # Update deck if provided
        if deck_id is not None:
            # Validate deck exists and user owns it
            deck = DeckService.get_deck_by_id(deck_id, user_id)
            flashcard.deck_id = deck_id
        
        db.session.commit()
        
        return flashcard
    
    @staticmethod
    def delete_flashcard(flashcard_id, user_id):
        """
        Delete a flashcard.
        
        Args:
            flashcard_id: ID of the flashcard to delete
            user_id: ID of the user making the deletion
            
        Raises:
            NotFoundError: If flashcard not found
            AuthorizationError: If user doesn't own the flashcard
        """
        flashcard = FlashcardService.get_flashcard_by_id(flashcard_id, user_id)
        
        db.session.delete(flashcard)
        db.session.commit()
    
    @staticmethod
    def get_user_flashcards(user_id, deck_id=None):
        """
        Get all flashcards for a user, optionally filtered by deck.
        
        Args:
            user_id: ID of the user
            deck_id: Optional deck ID to filter by
            
        Returns:
            List of Flashcard objects ordered by creation date (newest first)
        """
        query = Flashcard.query.filter_by(user_id=user_id)
        
        if deck_id:
            query = query.filter_by(deck_id=deck_id)
        
        return query.order_by(Flashcard.date_created.desc()).all()
    
    @staticmethod
    def bulk_create_flashcards(user_id, flashcards_data, deck_id=None):
        """
        Create multiple flashcards at once (useful for AI generation).
        
        Args:
            user_id: ID of the user creating the flashcards
            flashcards_data: List of dicts with 'question' and 'answer' keys
            deck_id: Optional deck ID (uses default deck if not provided)
            
        Returns:
            List of created Flashcard objects
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If user or deck not found
        """
        # Validate user exists
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        # Handle deck assignment
        if deck_id:
            deck = DeckService.get_deck_by_id(deck_id, user_id)
        else:
            deck = DeckService.get_default_deck(user_id)
            deck_id = deck.id
        
        # Validate flashcards data
        if not flashcards_data or len(flashcards_data) == 0:
            raise ValidationError("At least one flashcard is required")
        
        created_flashcards = []
        
        for idx, fc_data in enumerate(flashcards_data):
            question = fc_data.get('question', '').strip()
            answer = fc_data.get('answer', '').strip()
            
            if not question:
                raise ValidationError(f"Question is required for flashcard {idx + 1}")
            
            if not answer:
                raise ValidationError(f"Answer is required for flashcard {idx + 1}")
            
            flashcard = Flashcard(
                question=question,
                answer=answer,
                user_id=user_id,
                deck_id=deck_id
            )
            
            db.session.add(flashcard)
            created_flashcards.append(flashcard)
        
        db.session.commit()
        
        return created_flashcards