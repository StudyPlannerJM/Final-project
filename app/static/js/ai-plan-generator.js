// AI Plan Generator - Form submission handler with loading indicator
document.addEventListener('DOMContentLoaded', function() {
    const planForm = document.querySelector('.plan-form');
    const loadingIndicator = document.getElementById('loading-indicator');
    const formSection = document.querySelector('.form-section');
    const submitButton = document.querySelector('.btn-generate');
    const progressFill = document.querySelector('.progress-bar-fill');
    
    if (planForm && loadingIndicator && formSection && submitButton && progressFill) {
        planForm.addEventListener('submit', function() {
            loadingIndicator.classList.remove('is-hidden');
            formSection.style.opacity = '0.5';
            submitButton.disabled = true;
            
            // Animate progress bar
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
