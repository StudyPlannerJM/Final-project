// =============================================================================
// EVENT DETAILS MODALS
// Modal handlers for displaying event and task details
// =============================================================================

import { getCategoryColor } from './utils.js';

/**
 * Show Google Calendar event details in modal
 * @param {Object} event - Calendar event object
 */
export function showCalendarEventDetails(event) {
    const taskDetailsModal = document.getElementById('taskDetailsModal');
    if (!taskDetailsModal) return;

    // Update modal title
    document.getElementById('taskDetailsTitle').textContent = 'Google Calendar Event';

    // Populate modal with event details
    document.getElementById('detailTitle').textContent = event.title || 'No title';

    const descEl = document.getElementById('detailDescription');
    if (event.description) {
        descEl.textContent = event.description;
        descEl.classList.remove('empty');
    } else {
        descEl.textContent = 'No description provided';
        descEl.classList.add('empty');
    }

    // Format dates
    const startDate = new Date(event.start);
    const endDate = new Date(event.end);
    document.getElementById('detailDueDate').textContent = startDate.toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }) + ' - ' + endDate.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });

    // Hide category and status for calendar events
    document.getElementById('detailCategory').parentElement.style.display = 'none';
    document.getElementById('detailStatus').parentElement.style.display = 'none';

    // Hide edit button for Google Calendar events
    const editTaskBtn = document.getElementById('editTaskBtn');
    if (editTaskBtn) {
        editTaskBtn.style.display = 'none';
    }

    // Show modal
    taskDetailsModal.classList.add('active');
}

/**
 * Show task details in modal
 * @param {Object} task - Task object
 */
export function showTaskDetails(task) {
    const taskDetailsModal = document.getElementById('taskDetailsModal');
    if (!taskDetailsModal) return;

    // Reset modal title
    document.getElementById('taskDetailsTitle').textContent = 'Task Details';

    // Populate modal with task details
    document.getElementById('detailTitle').textContent = task.title || 'No title';

    const descEl = document.getElementById('detailDescription');
    if (task.description) {
        descEl.textContent = task.description;
        descEl.classList.remove('empty');
    } else {
        descEl.textContent = 'No description provided';
        descEl.classList.add('empty');
    }

    // Format due date
    if (task.due_date) {
        const dueDate = new Date(task.due_date.replace(' ', 'T'));
        document.getElementById('detailDueDate').textContent = dueDate.toLocaleString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } else {
        document.getElementById('detailDueDate').textContent = 'No due date';
    }

    document.getElementById('detailCategory').parentElement.style.display = 'flex';
    document.getElementById('detailCategory').parentElement.querySelector('.detail-label').innerHTML = '<i class="fas fa-folder"></i> Category:';

    // Display category with color and icon if available
    const categoryEl = document.getElementById('detailCategory');
    if (task.category) {
        if (typeof task.category === 'object' && task.category.name) {
            categoryEl.textContent = task.category.name;
            categoryEl.style.color = task.category.color || '#666';
        } else {
            categoryEl.textContent = task.category;
            categoryEl.style.color = getCategoryColor(task.category);
        }
    } else {
        categoryEl.textContent = 'No category';
        categoryEl.style.color = '#666';
    }

    document.getElementById('detailStatus').parentElement.style.display = 'flex';
    document.getElementById('detailStatus').parentElement.querySelector('.detail-label').innerHTML = '<i class="fas fa-tasks"></i> Status:';

    const statusEl = document.getElementById('detailStatus');
    statusEl.textContent = task.status || 'Not started';
    statusEl.className = `status-badge status-${task.status}`;

    // Show edit button for tasks
    const editTaskBtn = document.getElementById('editTaskBtn');
    if (editTaskBtn) {
        editTaskBtn.style.display = 'inline-block';
        editTaskBtn.onclick = function () {
            window.location.href = `/tasks/edit/${task.id}`;
        };
    }

    // Show modal
    taskDetailsModal.classList.add('active');
}

/**
 * Close task details modal
 */
export function closeTaskDetailsModal() {
    const taskDetailsModal = document.getElementById('taskDetailsModal');
    if (taskDetailsModal) {
        taskDetailsModal.classList.remove('active');
    }
}
