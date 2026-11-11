// Edit Task - Delete modal handler
function confirmDelete(deleteUrl) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = deleteUrl;
    addCsrfField(form); // csrf_token
    document.body.appendChild(form);
    form.submit();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const deleteButton = document.querySelector('.open-delete-task-modal');
    if (!deleteButton || !window.BrainDumpDeleteModal) {
        return;
    }

    deleteButton.addEventListener('click', function() {
        const deleteUrl = deleteButton.getAttribute('data-delete-url');
        window.BrainDumpDeleteModal.open({
            message: 'Are you sure you want to delete this task?',
            onConfirm: function() {
                confirmDelete(deleteUrl);
            }
        });
    });
});
