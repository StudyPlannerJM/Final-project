// ==============================================================================
// FLASHCARD MANAGEMENT JAVASCRIPT
// ==============================================================================

let flashcardToDelete = null;
let deckToDelete = null;
let deleteType = null; // 'flashcard' or 'deck'

/**
 * Initialize flashcard page functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeFlashcards();
    initializeDeckColors();
    initializeDeleteButtons();
});

/**
 * Initialize flashcard flip functionality
 */
function initializeFlashcards() {
    document.querySelectorAll('.btn-flip').forEach(button => {
        button.addEventListener('click', function() {
            const flashcard = this.closest('.flashcard-item');
            flashcard.classList.toggle('flipped');
        });
    });
}

/**
 * Initialize deck color styling
 */
function initializeDeckColors() {
    // Style deck cards
    document.querySelectorAll('.deck-card[data-color]').forEach(card => {
        const color = card.getAttribute('data-color');
        const lightColor1 = color + '08';
        const lightColor2 = color + '15';
        card.style.setProperty('--deck-color', color);
        card.style.setProperty('--deck-color-light1', lightColor1);
        card.style.setProperty('--deck-color-light2', lightColor2);
    });
    
    // Style flashcard deck indicators
    document.querySelectorAll('.flashcard-deck-indicator[data-color]').forEach(indicator => {
        const color = indicator.getAttribute('data-color');
        indicator.style.setProperty('--deck-indicator-color', color);
    });
}

/**
 * Initialize delete button functionality
 */
function initializeDeleteButtons() {
    // Flashcard delete buttons
    document.querySelectorAll('.delete-flashcard-btn').forEach(button => {
        button.addEventListener('click', function() {
            const flashcardId = this.dataset.flashcardId;
            showDeleteFlashcardModal(flashcardId);
        });
    });
    
    // Deck delete buttons
    document.querySelectorAll('.delete-deck-btn').forEach(button => {
        button.addEventListener('click', function() {
            const deckId = this.dataset.deckId;
            const deckName = this.dataset.deckName;
            const flashcardCount = this.dataset.flashcardCount;
            showDeleteDeckModal(deckId, deckName, flashcardCount);
        });
    });
    
    // Set up confirm button
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', confirmDelete);
    }
    
    // Close modal when clicking overlay
    document.addEventListener('click', function(event) {
        const modal = document.getElementById('deleteModal');
        if (modal && event.target === modal) {
            closeDeleteModal();
        }
    });
}

/**
 * Show delete confirmation modal for flashcard
 */
function showDeleteFlashcardModal(flashcardId) {
    flashcardToDelete = flashcardId;
    deckToDelete = null;
    deleteType = 'flashcard';
    document.getElementById('deleteModalMessage').textContent = 'Are you sure you want to delete this flashcard?';
    document.getElementById('deleteModal').style.display = 'flex';
}

/**
 * Show delete confirmation modal for deck
 */
function showDeleteDeckModal(deckId, deckName, flashcardCount) {
    deckToDelete = deckId;
    flashcardToDelete = null;
    deleteType = 'deck';
    const message = `Delete deck '${deckName}' and all ${flashcardCount} flashcard(s)?`;
    document.getElementById('deleteModalMessage').textContent = message;
    document.getElementById('deleteModal').style.display = 'flex';
}

/**
 * Close delete confirmation modal
 */
window.closeDeleteModal = function() {
    document.getElementById('deleteModal').style.display = 'none';
    flashcardToDelete = null;
    deckToDelete = null;
    deleteType = null;
}

/**
 * Confirm and execute deletion
 */
function confirmDelete() {
    if (deleteType === 'flashcard' && flashcardToDelete) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/flashcards/delete/${flashcardToDelete}`;
        document.body.appendChild(form);
        form.submit();
    } else if (deleteType === 'deck' && deckToDelete) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/flashcards/delete_deck/${deckToDelete}`;
        document.body.appendChild(form);
        form.submit();
    }
}
