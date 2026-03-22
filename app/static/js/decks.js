// ============================================================================== 
// DECK MANAGEMENT JAVASCRIPT 
// ============================================================================== 

// Only keep deck feature logic. Delete modal handled globally by delete-modal.js

/**
 * Initialize color picker preview
 */
function initializeColorPicker() {
    const colorInput = document.getElementById('color');
    const preview = document.getElementById('colorPreview');
    if (colorInput && preview) {
        colorInput.addEventListener('input', function() {
            preview.style.backgroundColor = colorInput.value;
        });
        preview.style.backgroundColor = colorInput.value;
    }
}

function initializeDeckCardColors() {
    document.querySelectorAll('.deck-card[data-color]').forEach(card => {
        const color = card.getAttribute('data-color');
        card.style.setProperty('--deck-color', color);
    });
}

function initializeIconButtons() {
    document.querySelectorAll('.icon-picker-btn').forEach(button => {
        button.addEventListener('click', function() {
            const iconClass = button.getAttribute('data-icon');
            // ...existing code for icon selection...
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initializeColorPicker();
    initializeDeckCardColors();
    initializeIconButtons();
    // Delete modal handled globally by delete-modal.js
});
