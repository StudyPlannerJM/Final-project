"""
Deck service for business logic related to flashcard decks
"""

from app import db
from app.models import Deck, User
from app.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)


class DeckService:
    """Service class for deck operations"""
    
    @staticmethod
    def create_deck(user_id, name, description=None, color='#3498db', icon=None):
        """
        Create a new deck with validation.
        
        Args:
            user_id: ID of the user creating the deck
            name: Deck name
            description: Optional deck description
            color: Hex color code for the deck (default: #3498db)
            icon: Optional FontAwesome icon name
            
        Returns:
            Created Deck object
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If user not found
        """
        # Validate name
        if not name or len(name.strip()) < 1:
            raise ValidationError("Deck name is required")
        
        if len(name.strip()) > 100:
            raise ValidationError("Deck name must not exceed 100 characters")
        
        # Validate user exists
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        # Check for duplicate deck name for this user
        existing_deck = Deck.query.filter_by(
            user_id=user_id, 
            name=name.strip()
        ).first()
        
        if existing_deck:
            raise ValidationError(
                f"You already have a deck named '{name.strip()}'"
            )
        
        # Validate color format (basic hex color validation)
        if color and not color.startswith('#'):
            raise ValidationError("Color must be a valid hex code starting with #")
        
        # Create deck
        deck = Deck(
            name=name.strip(),
            description=description.strip() if description else None,
            color=color,
            icon=icon,
            user_id=user_id,
            is_default=False
        )
        
        db.session.add(deck)
        db.session.commit()
        
        return deck
    
    @staticmethod
    def get_user_decks(user_id):
        """
        Get all decks for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of Deck objects ordered by name
        """
        return Deck.query.filter_by(user_id=user_id).order_by(Deck.name).all()  # type: ignore
    
    @staticmethod
    def get_deck_by_id(deck_id, user_id):
        """
        Get a specific deck by ID with authorization check.
        
        Args:
            deck_id: ID of the deck
            user_id: ID of the user requesting the deck
            
        Returns:
            Deck object
            
        Raises:
            NotFoundError: If deck not found
            AuthorizationError: If user doesn't own the deck
        """
        deck = db.session.get(Deck, deck_id)
        
        if not deck:
            raise NotFoundError(f"Deck with id {deck_id} not found")
        
        if deck.user_id != user_id:
            raise AuthorizationError(
                "You are not authorized to access this deck"
            )
        
        return deck
    
    @staticmethod
    def update_deck(deck_id, user_id, name=None, description=None, color=None, icon=None):
        """
        Update a deck's properties.
        
        Args:
            deck_id: ID of the deck to update
            user_id: ID of the user making the update
            name: Optional new name
            description: Optional new description
            color: Optional new color
            icon: Optional new icon
            
        Returns:
            Updated Deck object
            
        Raises:
            NotFoundError: If deck not found
            AuthorizationError: If user doesn't own the deck
            ValidationError: If validation fails
        """
        deck = DeckService.get_deck_by_id(deck_id, user_id)
        
        # Update name if provided
        if name is not None:
            if not name or len(name.strip()) < 1:
                raise ValidationError("Deck name is required")
            
            if len(name.strip()) > 100:
                raise ValidationError("Deck name must not exceed 100 characters")
            
            # Check for duplicate name (excluding current deck)
            existing_deck = Deck.query.filter(
                Deck.user_id == user_id,  # type: ignore
                Deck.name == name.strip(),  # type: ignore
                Deck.id != deck_id  # type: ignore
            ).first()
            
            if existing_deck:
                raise ValidationError(
                    f"You already have a deck named '{name.strip()}'"
                )
            
            deck.name = name.strip()
        
        # Update description if provided
        if description is not None:
            deck.description = description.strip() if description else None
        
        # Update color if provided
        if color is not None:
            if color and not color.startswith('#'):
                raise ValidationError("Color must be a valid hex code starting with #")
            deck.color = color
        
        # Update icon if provided
        if icon is not None:
            deck.icon = icon
        
        db.session.commit()
        
        return deck
    
    @staticmethod
    def delete_deck(deck_id, user_id):
        """
        Delete a deck and all its flashcards.
        
        Args:
            deck_id: ID of the deck to delete
            user_id: ID of the user making the deletion
            
        Raises:
            NotFoundError: If deck not found
            AuthorizationError: If user doesn't own the deck
            ValidationError: If trying to delete the default deck
        """
        deck = DeckService.get_deck_by_id(deck_id, user_id)
        
        # Prevent deletion of default deck
        if deck.is_default:
            raise ValidationError(
                "Cannot delete the default deck. Please create a new default deck first."
            )
        
        # Delete the deck (cascade will delete associated flashcards)
        db.session.delete(deck)
        db.session.commit()
    
    @staticmethod
    def get_or_create_deck(user_id, name, description=None, color='#3498db', icon=None):
        """
        Get an existing deck by name or create a new one.
        Useful for AI-generated flashcards that auto-create decks.
        
        Args:
            user_id: ID of the user
            name: Deck name to find or create
            description: Optional description for new deck
            color: Color for new deck
            icon: Icon for new deck
            
        Returns:
            Existing or newly created Deck object
        """
        # Try to find existing deck
        deck = Deck.query.filter_by(
            user_id=user_id,
            name=name.strip()
        ).first()
        
        if deck:
            return deck
        
        # Create new deck if not found
        return DeckService.create_deck(
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            icon=icon
        )
    
    @staticmethod
    def get_default_deck(user_id):
        """
        Get the default deck for a user. Create one if it doesn't exist.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Default Deck object
        """
        # Try to find existing default deck
        default_deck = Deck.query.filter_by(
            user_id=user_id,
            is_default=True
        ).first()
        
        if default_deck:
            return default_deck
        
        # Create default deck if not found
        deck = Deck(
            name='General',
            description='Default deck for flashcards',
            color='#3498db',
            icon='fa-layer-group',
            user_id=user_id,
            is_default=True
        )
        
        db.session.add(deck)
        db.session.commit()
        
        return deck