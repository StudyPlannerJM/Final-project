// ==============================================================================
// DECK MANAGEMENT JAVASCRIPT
// ==============================================================================

/**
 * Initialize color picker preview
 */
function initializeColorPicker() {
    const colorInput = document.getElementById('color');
    const preview = document.getElementById('colorPreview');
    
    if (colorInput && preview) {
        // Set initial preview color
        preview.style.backgroundColor = colorInput.value;
        
        // Update preview on color change
        colorInput.addEventListener('input', function() {
            preview.style.backgroundColor = this.value;
        });
    }
}

function initializeDeckCardColors() {
    document.querySelectorAll('.deck-card[data-color]').forEach((card) => {
        const color = card.getAttribute('data-color');
        if (!color) {
            return;
        }

        const lightColor1 = color + '08';
        const lightColor2 = color + '15';

        card.style.setProperty('--deck-color', color);
        card.style.setProperty('--deck-color-light1', lightColor1);
        card.style.setProperty('--deck-color-light2', lightColor2);
    });
}

/**
 * Set deck icon from suggestion buttons
 * @param {string} iconClass - Font Awesome icon class (e.g., 'fa-book')
 */
function setIcon(iconClass, triggerButton) {
    const iconInput = document.getElementById('icon');
    if (iconInput) {
        iconInput.value = iconClass;
        
        // Update the current icon preview
        const currentIconElement = document.getElementById('currentIconElement');
        const currentIconText = document.getElementById('currentIconText');
        if (currentIconElement) {
            currentIconElement.className = 'fas ' + iconClass;
        }
        if (currentIconText) {
            currentIconText.textContent = iconClass;
        }
        
        // Visual feedback on buttons
        const buttons = document.querySelectorAll('.icon-btn');
        buttons.forEach(btn => {
            btn.style.backgroundColor = '';
            btn.style.color = '';
            btn.style.borderColor = '';
        });

        if (triggerButton) {
            triggerButton.style.backgroundColor = '#3498db';
            triggerButton.style.color = 'white';
            triggerButton.style.borderColor = '#3498db';
        }
    }
}

function initializeIconButtons() {
    document.querySelectorAll('.icon-btn[data-icon]').forEach((button) => {
        button.addEventListener('click', function () {
            const iconClass = button.getAttribute('data-icon');
            setIcon(iconClass, button);
        });
    });
}

/**
 * Confirm before deleting a deck — uses the custom BrainDump modal
 * @param {number} deckId - The ID of the deck to delete
 */
function confirmDeleteDeck(deckId) {
    deckToDelete = deckId;
    const msgEl = document.getElementById('deleteModalMessage');
    if (msgEl) {
        msgEl.textContent = 'Are you sure you want to delete this deck? All flashcards in this deck will be moved to the default deck.';
    }
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

// ==============================================================================
// DELETE MODAL FUNCTIONALITY
// ==============================================================================

let deckToDelete = null;

/**
 * Show delete confirmation modal for deck
 */
function showDeleteDeckModal(deckId, deckName, flashcardCount) {
    deckToDelete = deckId;
    const message = `Delete deck '${deckName}' and all ${flashcardCount} flashcard(s)?`;
    document.getElementById('deleteModalMessage').textContent = message;
    document.getElementById('deleteModal').style.display = 'flex';
}

/**
 * Close delete confirmation modal
 */
window.closeDeleteModal = function() {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.style.display = 'none';
        deckToDelete = null;
    }
}

/**
 * Confirm and execute deck deletion
 */
function confirmDelete() {
    if (deckToDelete) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/flashcards/delete_deck/${deckToDelete}`;
        document.body.appendChild(form);
        form.submit();
    }
}

/**
 * Initialize delete button functionality
 */
function initializeDeleteButtons() {
    // Delete deck buttons
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeColorPicker();
    initializeDeckCardColors();
    initializeIconButtons();
    initializeDeleteButtons();
});
