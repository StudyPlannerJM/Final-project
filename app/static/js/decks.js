// ==============================================================================
// DECK MANAGEMENT JAVASCRIPT
// ==============================================================================

/**
 * Initialize color picker preview
 */
function initializeColorPicker() {
    const colorInput = document.getElementById('color');
    const preview = document.getElementById('color-preview');
    
    if (colorInput && preview) {
        // Set initial preview color
        preview.style.backgroundColor = colorInput.value;
        
        // Update preview on color change
        colorInput.addEventListener('input', function() {
            preview.style.backgroundColor = this.value;
        });
    }
}

/**
 * Set deck icon from suggestion buttons
 * @param {string} iconClass - Font Awesome icon class (e.g., 'fa-book')
 */
function setIcon(iconClass) {
    const iconInput = document.getElementById('icon');
    if (iconInput) {
        iconInput.value = iconClass;
        
        // Visual feedback
        const buttons = document.querySelectorAll('.icon-btn');
        buttons.forEach(btn => {
            btn.style.backgroundColor = '';
            btn.style.color = '';
            btn.style.borderColor = '';
        });
        
        event.target.closest('.icon-btn').style.backgroundColor = '#3498db';
        event.target.closest('.icon-btn').style.color = 'white';
        event.target.closest('.icon-btn').style.borderColor = '#3498db';
    }
}

/**
 * Confirm before deleting a deck
 * @param {number} deckId - The ID of the deck to delete
 */
function confirmDeleteDeck(deckId) {
    if (confirm('Are you sure you want to delete this deck? All flashcards in this deck will be moved to the default deck.')) {
        window.location.href = `/delete_deck/${deckId}`;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeColorPicker();
});
