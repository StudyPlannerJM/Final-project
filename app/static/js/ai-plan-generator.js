// AI Plan Generator - Form submission handler with loading indicator
document.addEventListener('DOMContentLoaded', function() {
    const planForm = document.querySelector('.plan-form');
    
    if (planForm) {
        planForm.addEventListener('submit', function() {
            document.getElementById('loading-indicator').style.display = 'block';
            document.querySelector('.form-section').style.opacity = '0.5';
            document.querySelector('.btn-generate').disabled = true;
            
            // Animate progress bar
            const progressFill = document.querySelector('.progress-bar-fill');
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
