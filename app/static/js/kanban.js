const taskCards = document.querySelectorAll('.task-card');
const columns = document.querySelectorAll('.column-content');
const TOUCH_DRAG_THRESHOLD = 60;
const AUTO_SCROLL_EDGE_PX = 90;
const AUTO_SCROLL_STEP = 16;

let activeTouchDrag = null;

taskCards.forEach((card) => {
    registerDesktopDrag(card);
    registerTouchDrag(card);
});

columns.forEach((column) => {
    column.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        column.classList.add('drag-over');
    });

    column.addEventListener('dragleave', (e) => {
        if (e.target === column) {
            column.classList.remove('drag-over');
        }
    });

    column.addEventListener('drop', (e) => {
        e.preventDefault();
        column.classList.remove('drag-over');

        const taskId = e.dataTransfer.getData('taskId');
        const newStatus = column.dataset.status;
        const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);

        if (taskCard) {
            updateTaskStatus(taskId, newStatus, taskCard);
        }
    });
});

function registerDesktopDrag(card) {
    card.addEventListener('dragstart', (e) => {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('taskId', card.dataset.taskId);
        card.classList.add('dragging');
    });

    card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
        clearColumnHighlights();
    });
}

function registerTouchDrag(card) {
    card.addEventListener('touchstart', onTouchStart, { passive: true });
    card.addEventListener('touchmove', onTouchMove, { passive: false });
    card.addEventListener('touchend', onTouchEnd);
    card.addEventListener('touchcancel', cancelTouchDrag);

    function onTouchStart(e) {
        if (isInteractiveElement(e.target)) {
            return;
        }

        const touch = e.changedTouches[0];
        const rect = card.getBoundingClientRect();

        activeTouchDrag = {
            card,
            taskId: card.dataset.taskId,
            startX: touch.clientX,
            startY: touch.clientY,
            lastX: touch.clientX,
            lastY: touch.clientY,
            offsetX: touch.clientX - rect.left,
            offsetY: touch.clientY - rect.top,
            width: rect.width,
            isDragging: false
        };
    }

    function onTouchMove(e) {
        if (!activeTouchDrag || activeTouchDrag.card !== card) {
            return;
        }

        const touch = e.changedTouches[0];
        activeTouchDrag.lastX = touch.clientX;
        activeTouchDrag.lastY = touch.clientY;

        const dx = touch.clientX - activeTouchDrag.startX;
        const dy = touch.clientY - activeTouchDrag.startY;

        if (!activeTouchDrag.isDragging) {
            if (Math.hypot(dx, dy) < TOUCH_DRAG_THRESHOLD) {
                return;
            }

            beginTouchDrag(activeTouchDrag);
        }

        e.preventDefault();
        moveDraggedCard(activeTouchDrag, touch.clientX, touch.clientY);
        highlightDropColumn(touch.clientX, touch.clientY);
        autoScrollDuringDrag(touch.clientX, touch.clientY);
    }

    function onTouchEnd(e) {
        if (!activeTouchDrag || activeTouchDrag.card !== card) {
            return;
        }

        const dragState = activeTouchDrag;
        activeTouchDrag = null;

        if (!dragState.isDragging) {
            return;
        }

        e.preventDefault();

        const dropColumn = getColumnFromPoint(dragState.lastX, dragState.lastY);
        finishTouchDrag(dragState.card);

        if (!dropColumn) {
            return;
        }

        const newStatus = dropColumn.dataset.status;
        updateTaskStatus(dragState.taskId, newStatus, dragState.card);
    }
}

function beginTouchDrag(dragState) {
    const { card, width } = dragState;
    dragState.isDragging = true;
    card.classList.add('dragging', 'touch-dragging');
    card.style.width = `${width}px`;
    card.style.position = 'fixed';
    card.style.zIndex = '1300';
    card.style.pointerEvents = 'none';
}

function moveDraggedCard(dragState, clientX, clientY) {
    const { card, offsetX, offsetY } = dragState;
    card.style.left = `${clientX - offsetX}px`;
    card.style.top = `${clientY - offsetY}px`;
}

function finishTouchDrag(card) {
    card.classList.remove('dragging', 'touch-dragging');
    card.style.position = '';
    card.style.left = '';
    card.style.top = '';
    card.style.width = '';
    card.style.zIndex = '';
    card.style.pointerEvents = '';
    clearColumnHighlights();
}

function cancelTouchDrag() {
    if (!activeTouchDrag) {
        return;
    }

    const dragState = activeTouchDrag;
    activeTouchDrag = null;

    if (dragState.isDragging) {
        finishTouchDrag(dragState.card);
    }
}

function highlightDropColumn(clientX, clientY) {
    clearColumnHighlights();
    const targetColumn = getColumnFromPoint(clientX, clientY);

    if (targetColumn) {
        targetColumn.classList.add('drag-over');
    }
}

function getColumnFromPoint(clientX, clientY) {
    const element = document.elementFromPoint(clientX, clientY);
    if (!element) {
        return null;
    }

    const directContent = element.closest('.column-content');
    if (directContent) {
        return directContent;
    }

    const columnContainer = element.closest('.kanban-column');
    return columnContainer ? columnContainer.querySelector('.column-content') : null;
}

function autoScrollDuringDrag(clientX, clientY) {
    if (clientY < AUTO_SCROLL_EDGE_PX) {
        window.scrollBy(0, -AUTO_SCROLL_STEP);
    } else if (window.innerHeight - clientY < AUTO_SCROLL_EDGE_PX) {
        window.scrollBy(0, AUTO_SCROLL_STEP);
    }

    const hoveredColumn = getColumnFromPoint(clientX, clientY);
    if (!hoveredColumn) {
        return;
    }

    const rect = hoveredColumn.getBoundingClientRect();
    const withinTopEdge = clientY - rect.top;
    const withinBottomEdge = rect.bottom - clientY;

    if (withinTopEdge > 0 && withinTopEdge < 56) {
        hoveredColumn.scrollTop -= AUTO_SCROLL_STEP;
    } else if (withinBottomEdge > 0 && withinBottomEdge < 56) {
        hoveredColumn.scrollTop += AUTO_SCROLL_STEP;
    }
}

function clearColumnHighlights() {
    columns.forEach((col) => col.classList.remove('drag-over'));
}

function isInteractiveElement(element) {
    return Boolean(element.closest('a, button, input, textarea, select, label'));
}

// ===== BACKEND COMMUNICATION =====
/**
 * Send the status update to the server
 * @param {number} taskId - The ID of the task being updated
 * @param {string} newStatus - The new status: 'todo', 'doing', or 'done'
 * @param {Element} taskCard - The DOM element of the task
 */
function updateTaskStatus(taskId, newStatus, taskCard) {
    const currentStatus = taskCard.closest('.column-content')?.dataset.status;
    if (currentStatus === newStatus) {
        return;
    }

    // Construct the URL for the backend route
    const url = `/tasks/update_status/${taskId}/${newStatus}`;

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