const taskCards = document.querySelectorAll('.task-card');
const columns = document.querySelectorAll('.column-content');
const TOUCH_DRAG_THRESHOLD = 60;
const AUTO_SCROLL_EDGE_PX = 90;
const AUTO_SCROLL_STEP = 16;

let activeTouchDrag = null;

const phoneQuery = window.matchMedia('(max-width: 767.98px)');
const STATUS_LABELS = { todo: 'To-Do', doing: 'Doing', done: 'Done' };

const notify = (message, category) => {
    if (window.BrainDump && window.BrainDump.toast) {
        window.BrainDump.toast(message, category);
    }
};

taskCards.forEach((card) => {
    registerDesktopDrag(card);
    registerTouchDrag(card);
    registerMoveSelect(card);
});

initBoardTabs();
taskCards.forEach(refreshOverdue);

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
        if (phoneQuery.matches || isInteractiveElement(e.target)) {
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

// ===== "MOVE TO" CONTROL =====
function registerMoveSelect(card) {
    const select = card.querySelector('.task-move');
    if (!select) return;
    select.addEventListener('change', () => {
        const newStatus = select.value;
        if (!newStatus) return;
        updateTaskStatus(card.dataset.taskId, newStatus, card);
    });
}

function refreshMoveSelect(card, status) {
    const select = card.querySelector('.task-move');
    if (!select) return;
    select.innerHTML = '';
    const placeholder = new Option('Move to\u2026', '', true, true);
    placeholder.disabled = true;
    select.add(placeholder);
    Object.entries(STATUS_LABELS).forEach(([value, label]) => {
        if (value !== status) select.add(new Option(label, value));
    });
}

function resetMoveSelect(card) {
    const select = card.querySelector('.task-move');
    if (select) select.selectedIndex = 0;
}

// ===== OVERDUE MARKER =====
// data-due is the due date as the user entered it (wall-clock, no timezone),
// so comparing it with the browser's clock is correct wherever the server runs.
function refreshOverdue(card) {
    const due = card.dataset.due ? new Date(card.dataset.due) : null;
    const status = card.closest('.column-content')?.dataset.status;
    const overdue = Boolean(due) && !Number.isNaN(due.getTime()) && due < new Date() && status !== 'done';
    card.classList.toggle('is-overdue', overdue);
    let label = card.querySelector('.task-overdue-label');
    if (overdue && !label) {
        const dueLine = card.querySelector('.task-due-date');
        if (dueLine) {
            label = document.createElement('span');
            label.className = 'task-overdue-label';
            label.textContent = 'Overdue';
            dueLine.appendChild(label);
        }
    } else if (!overdue && label) {
        label.remove();
    }
}

// ===== COLUMN TABS (phones) =====
function initBoardTabs() {
    const board = document.querySelector('.kanban-board');
    const tabs = Array.from(document.querySelectorAll('.board-tab'));
    if (!board || !tabs.length) return;

    let programmaticUntil = 0;

    const setActive = (status) => {
        tabs.forEach((tab) => {
            const active = tab.dataset.status === status;
            tab.classList.toggle('is-active', active);
            tab.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    };

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            const column = document.getElementById('column-' + tab.dataset.status);
            if (!column) return;
            programmaticUntil = Date.now() + 600;
            board.scrollTo({ left: column.offsetLeft - board.offsetLeft, behavior: 'smooth' });
            setActive(tab.dataset.status);
        });
    });

    const syncFromScroll = () => {
        const columns = Array.from(board.querySelectorAll('.kanban-column'));
        const centre = board.scrollLeft + board.clientWidth / 2;
        const current = columns.find((column) => {
            const left = column.offsetLeft - board.offsetLeft;
            return centre >= left && centre < left + column.offsetWidth;
        });
        if (current) setActive(current.dataset.column);
    };

    // Keep the tabs in step with swiping (ignored while a tab tap is scrolling the board)
    let ticking = false;
    board.addEventListener('scroll', () => {
        if (ticking || Date.now() < programmaticUntil) return;
        ticking = true;
        requestAnimationFrame(() => {
            ticking = false;
            syncFromScroll();
        });
    }, { passive: true });

    const onLayoutChange = () => syncFromScroll();
    if (phoneQuery.addEventListener) {
        phoneQuery.addEventListener('change', onLayoutChange);
    } else {
        phoneQuery.addListener(onLayoutChange);
    }
}

// ===== BACKEND COMMUNICATION =====
/**
 * Send the status update to the server and move the card when it succeeds.
 * On any failure the card stays where it was and the user is told.
 * @param {number} taskId - The ID of the task being updated
 * @param {string} newStatus - The new status: 'todo', 'doing', or 'done'
 * @param {Element} taskCard - The DOM element of the task
 */
function updateTaskStatus(taskId, newStatus, taskCard) {
    const currentStatus = taskCard.closest('.column-content')?.dataset.status;
    if (currentStatus === newStatus) {
        resetMoveSelect(taskCard);
        return;
    }

    const url = `/tasks/update_status/${taskId}/${newStatus}`;
    taskCard.classList.add('is-saving');

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }
    })
    .then((response) => {
        // An expired session redirects to the login page instead of returning JSON
        const isJson = (response.headers.get('content-type') || '').includes('application/json');
        if (response.redirected) {
            throw Object.assign(new Error('Your session may have expired. Reload the page and sign in again.'), { userFacing: true });
        }
        if (!isJson) {
            throw Object.assign(new Error('The task could not be updated. Reload the page and try again.'), { userFacing: true });
        }
        return response.json().then((data) => {
            if (!response.ok || !data.success) {
                throw Object.assign(new Error(data.error || 'The task could not be updated.'), { userFacing: true });
            }
            return data;
        });
    })
    .then(() => {
        const targetColumn = document.querySelector(`.column-content[data-status="${newStatus}"]`);
        const emptyNote = targetColumn.querySelector('.column-empty');
        targetColumn.insertBefore(taskCard, emptyNote);
        refreshMoveSelect(taskCard, newStatus);
        refreshOverdue(taskCard);
        updateTaskCounts();
        notify(`Moved to ${STATUS_LABELS[newStatus]}`, 'success');
    })
    .catch((error) => {
        console.error('Error updating task:', error);
        resetMoveSelect(taskCard);
        notify(error.userFacing ? error.message : 'Could not reach the server. Check your connection and try again.', 'danger');
    })
    .finally(() => {
        taskCard.classList.remove('is-saving');
    });
}

// ===== UI UPDATES =====
function updateTaskCounts() {
    document.querySelectorAll('.column-content').forEach((column) => {
        const status = column.dataset.status;
        const count = column.querySelectorAll('.task-card').length;
        document.querySelectorAll(`.task-count[data-count-for="${status}"]`).forEach((el) => {
            el.textContent = count;
        });
        const emptyNote = column.querySelector('.column-empty');
        if (emptyNote) emptyNote.hidden = count > 0;
    });
}
