// Delete Modal Functionality
let taskIdToDelete = null;

function showDeleteModal(taskId) {
    taskIdToDelete = taskId;
    document.getElementById('deleteModal').hidden = false;
}

function closeDeleteModal() {
    document.getElementById('deleteModal').hidden = true;
    taskIdToDelete = null;
}

function confirmDelete() {
    if (taskIdToDelete) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/tasks/delete/${taskIdToDelete}`;
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

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.hidden = true;
    }

    document.querySelectorAll('.task-category[data-category-color]').forEach(function (categoryBadge) {
        const color = categoryBadge.getAttribute('data-category-color');
        if (color) {
            categoryBadge.style.setProperty('--category-color', color);
        }
    });
});
