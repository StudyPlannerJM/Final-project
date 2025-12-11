// Get all draggable task cards
const taskCards = document.querySelectorAll('.task-card');
// Get all droppable columns
const columns = document.querySelectorAll('.column-content');

// ===== DRAG START =====
taskCards.forEach(card => {
    card.addEventListener('dragstart', (e) => {
        // Store the task ID being dragged
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('taskId', card.dataset.taskId);
        // Visual feedback - fade out the card
        card.classList.add('dragging');
    });

    // Visual feedback when drag ends
    card.addEventListener('dragend', (e) => {
        card.classList.remove('dragging');
        // Remove highlight from all columns
        columns.forEach(col => col.classList.remove('drag-over'));
    });
});

// ===== DRAG OVER COLUMNS =====
columns.forEach(column => {
    // Allow dropping on the column
    column.addEventListener('dragover', (e) => {
        e.preventDefault(); // Necessary to allow drop
        e.dataTransfer.dropEffect = 'move';
        // Visual feedback - highlight the column
        column.classList.add('drag-over');
    });

    // Remove highlight when dragging leaves the column
    column.addEventListener('dragleave', (e) => {
        // Only remove if leaving the column itself, not child elements
        if (e.target === column) {
            column.classList.remove('drag-over');
        }
    });

    // Handle dropping the task
    column.addEventListener('drop', (e) => {
        e.preventDefault();
        column.classList.remove('drag-over');

        // Get the task ID being dropped
        const taskId = e.dataTransfer.getData('taskId');
        // Get the new status from the column's data attribute
        const newStatus = column.dataset.status;

        // Find the task card element
        const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);

        if (taskCard) {
            // Send update to backend
            updateTaskStatus(taskId, newStatus, taskCard);
        }
    });
});

// ===== BACKEND COMMUNICATION =====
/**
 * Send the status update to the server
 * @param {number} taskId - The ID of the task being updated
 * @param {string} newStatus - The new status: 'todo', 'doing', or 'done'
 * @param {Element} taskCard - The DOM element of the task
 */
function updateTaskStatus(taskId, newStatus, taskCard) {
    // Construct the URL for the backend route
    const url = `/update_task_status/${taskId}/${newStatus}`;

    // Send POST request to backend
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to update task');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Update successful - move the card visually
            // Find the target column and append the card
            const targetColumn = document.querySelector(`[data-status="${newStatus}"]`);
            targetColumn.appendChild(taskCard);

            // Update task counts
            updateTaskCounts();

            console.log(`Task ${taskId} moved to ${newStatus}`);
        } else {
            // Handle error
            console.error('Error:', data.error);
            alert('Failed to update task: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error updating task: ' + error.message);
        // Optionally reload the page if update fails
        // location.reload();
    });
}

// ===== UPDATE TASK COUNTS =====
/**
 * Update the task count badges in each column header
 * This shows how many tasks are in each column
 */
function updateTaskCounts() {
    const columns = document.querySelectorAll('.column-content');
    const countElements = document.querySelectorAll('.task-count');

    columns.forEach((column, index) => {
        // Count task cards in this column
        const taskCount = column.querySelectorAll('.task-card').length;
        // Update the count display
        countElements[index].textContent = taskCount;
    });
}