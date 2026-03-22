// ==============================================================================
// FLASHCARD MANAGEMENT JAVASCRIPT
// ==============================================================================


/**
 * Initialize flashcard page functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeFlashcards();
    initializeDeckColors();
    // Delete modal handled globally by delete-modal.js
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

