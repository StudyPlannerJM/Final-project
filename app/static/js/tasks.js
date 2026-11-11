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
        addCsrfField(form); // csrf_token
        document.body.appendChild(form);
        form.submit();
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.hidden = true;
    }

    const closeButtons = document.querySelectorAll('[data-task-delete-close]');
    closeButtons.forEach(function (button) {
        button.addEventListener('click', closeDeleteModal);
    });

    const confirmButton = document.getElementById('confirmDeleteBtn');
    if (confirmButton) {
        confirmButton.addEventListener('click', confirmDelete);
    }

    document.querySelectorAll('.delete-task-btn[data-task-id]').forEach(function (button) {
        button.addEventListener('click', function () {
            showDeleteModal(button.getAttribute('data-task-id'));
        });
    });

    document.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeDeleteModal();
        }
    });

    document.querySelectorAll('.task-category[data-category-color]').forEach(function (categoryBadge) {
        const color = categoryBadge.getAttribute('data-category-color');
        if (color) {
            categoryBadge.style.setProperty('--category-color', color);
        }
    });
});
