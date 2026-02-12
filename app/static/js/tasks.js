// Delete Modal Functionality
let taskIdToDelete = null;

function showDeleteModal(taskId) {
    taskIdToDelete = taskId;
    document.getElementById('deleteModal').style.display = 'flex';
}

function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    taskIdToDelete = null;
}

function confirmDelete() {
    if (taskIdToDelete) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/delete_task/${taskIdToDelete}`;
        document.body.appendChild(form);
        form.submit();
    }
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    const modal = document.getElementById('deleteModal');
    if (event.target === modal) {
        closeDeleteModal();
    }
});
