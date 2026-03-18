document.addEventListener('DOMContentLoaded', function () {
    let pendingDeleteForm = null;

    const modal = document.getElementById('adminDeleteModal');
    const message = document.getElementById('adminDeleteMessage');
    const confirmButton = document.getElementById('adminDeleteConfirmBtn');

    if (!modal || !message || !confirmButton) {
        return;
    }

    function closeModal() {
        modal.classList.remove('open');
        pendingDeleteForm = null;
    }

    document.querySelectorAll('.open-admin-delete-modal').forEach(function (button) {
        button.addEventListener('click', function () {
            const username = button.getAttribute('data-username');
            const formId = button.getAttribute('data-form-id');

            pendingDeleteForm = document.getElementById(formId);
            message.textContent = 'You are about to remove "' + username + '" from BrainDump.';
            modal.classList.add('open');
        });
    });

    document.querySelectorAll('[data-admin-delete-close]').forEach(function (button) {
        button.addEventListener('click', closeModal);
    });

    confirmButton.addEventListener('click', function () {
        if (pendingDeleteForm) {
            pendingDeleteForm.submit();
        }
        closeModal();
    });

    modal.addEventListener('click', function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });
});
