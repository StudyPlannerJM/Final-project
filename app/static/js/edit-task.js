// Edit Task - Delete modal handler
function showDeleteModal() {
    // Set custom message for task deletion
    document.getElementById('deleteModalMessage').textContent = 'Are you sure you want to delete this task?';
    document.getElementById('deleteModal').style.display = 'flex';
}

window.closeDeleteModal = function() {
    document.getElementById('deleteModal').style.display = 'none';
}

function confirmDelete() {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = deleteTaskUrl; // This will be set from the template
    document.body.appendChild(form);
    form.submit();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', confirmDelete);
    }
    
    // Close modal when clicking overlay
    document.addEventListener('click', function(event) {
        const modal = document.getElementById('deleteModal');
        if (event.target === modal) {
            closeDeleteModal();
        }
    });
});
