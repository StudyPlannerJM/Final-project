// Reusable delete modal helper for form-based confirmations.
(function () {
    let confirmHandler = null;

    function getModalElements() {
        const modal = document.getElementById('deleteModal');
        if (!modal) {
            return null;
        }

        return {
            modal,
            message: document.getElementById('deleteModalMessage'),
            confirmBtn: document.getElementById('confirmDeleteBtn'),
            closeButtons: modal.querySelectorAll('[data-delete-modal-close]')
        };
    }

    function close() {
        const elements = getModalElements();
        if (!elements) {
            return;
        }

        elements.modal.classList.add('is-hidden');
        confirmHandler = null;
    }

    function open(options) {
        const elements = getModalElements();
        if (!elements) {
            return;
        }

        const message = options && options.message ? options.message : 'Are you sure you want to delete this item?';
        confirmHandler = options && typeof options.onConfirm === 'function' ? options.onConfirm : null;

        if (elements.message) {
            elements.message.textContent = message;
        }

        elements.modal.classList.remove('is-hidden');
    }

    function bindFormDeleteTriggers() {
        document.querySelectorAll('.open-delete-modal').forEach((button) => {
            button.addEventListener('click', () => {
                const form = button.closest('form');
                const entity = button.getAttribute('data-delete-entity') || 'item';
                const label = button.getAttribute('data-delete-label');
                const message = label
                    ? `Are you sure you want to delete "${label}"?`
                    : `Are you sure you want to delete this ${entity}?`;

                open({
                    message,
                    onConfirm: () => {
                        if (form) {
                            form.submit();
                        }
                    }
                });
            });
        });
    }

    function initialize() {
        const elements = getModalElements();
        if (!elements) {
            return;
        }

        elements.confirmBtn.addEventListener('click', () => {
            if (confirmHandler) {
                confirmHandler();
            }
            close();
        });

        elements.closeButtons.forEach((button) => {
            button.addEventListener('click', close);
        });

        elements.modal.addEventListener('click', (event) => {
            if (event.target === elements.modal) {
                close();
            }
        });

        bindFormDeleteTriggers();
    }

    window.BrainDumpDeleteModal = {
        open,
        close,
        bindFormDeleteTriggers
    };

    document.addEventListener('DOMContentLoaded', initialize);
})();