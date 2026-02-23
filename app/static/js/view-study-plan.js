// View Study Plan - Flashcard generation loading indicator
document.addEventListener('DOMContentLoaded', function() {
    const flashcardForm = document.getElementById('flashcard-form');
    
    if (flashcardForm) {
        flashcardForm.addEventListener('submit', function() {
            document.getElementById('flashcard-loading').style.display = 'block';
            document.querySelector('.flashcard-options').style.opacity = '0.5';
            document.getElementById('flashcard-submit-btn').disabled = true;
            
            // Animate progress bar (same as AI plan generator)
            const progressFill = document.getElementById('flashcard-progress');
            let width = 0;
            const interval = setInterval(() => {
                if (width >= 90) {
                    clearInterval(interval);
                } else {
                    width += 1;
                    progressFill.style.width = width + '%';
                }
            }, 100);
        });
    }
});
