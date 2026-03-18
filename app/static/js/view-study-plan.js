// View Study Plan - Flashcard generation loading indicator
document.addEventListener('DOMContentLoaded', function() {
    const flashcardForm = document.getElementById('flashcard-form');
    const printButton = document.getElementById('printPlanBtn');
    const loading = document.getElementById('flashcard-loading');
    const options = document.querySelector('.flashcard-options');
    const submitButton = document.getElementById('flashcard-submit-btn');
    const progressFill = document.getElementById('flashcard-progress');

    if (printButton) {
        printButton.addEventListener('click', function() {
            window.print();
        });
    }
    
    if (flashcardForm && loading && options && submitButton && progressFill) {
        flashcardForm.addEventListener('submit', function() {
            loading.classList.remove('is-hidden');
            options.style.opacity = '0.5';
            submitButton.disabled = true;
            
            // Animate progress bar (same as AI plan generator)
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
