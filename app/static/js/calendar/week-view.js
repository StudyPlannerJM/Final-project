// =============================================================================
// WEEK VIEW RENDERER
// Renders the weekly calendar grid with events
// =============================================================================

import { formatTime, getDayNames, escapeHtml } from './utils.js';
import { showCalendarEventDetails, showTaskDetails } from './event-modals.js';
import { getCategoryColor } from './utils.js';
import { DAYS_PER_WEEK, HOURS_PER_DAY, HOUR_SLOT_HEIGHT } from './constants.js';

// Store events and tasks data for event delegation
let eventsDataMap = new Map();
let tasksDataMap = new Map();

/**
 * Render week view calendar
 * @param {Date} currentDate - Currently selected date
 * @param {Object[]} calendarEvents - Array of calendar events
 * @param {Object[]} tasks - Array of tasks
 */
export function renderWeekView(currentDate, calendarEvents, tasks) {
    // Clear previous data maps
    eventsDataMap.clear();
    tasksDataMap.clear();
    
    // Build week day headers
    const weekHeader = document.getElementById('weekDaysHeader');
    // Clear existing headers except the time column header
    while (weekHeader.children.length > 1) {
        weekHeader.removeChild(weekHeader.lastChild);
    }

    // Calculate the start of the week (Monday)
    const startOfWeek = new Date(currentDate);
    const dayOfWeek = startOfWeek.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // Adjust to Monday
    startOfWeek.setDate(startOfWeek.getDate() + diff);

    // Generate day headers (Monday to Sunday)
    for (let i = 0; i < DAYS_PER_WEEK; i++) {
        const day = new Date(startOfWeek);
        day.setDate(startOfWeek.getDate() + i);

        const isToday = day.toDateString() === new Date().toDateString();
        const isSelected = day.toDateString() === currentDate.toDateString();

        const dayHeader = document.createElement('div');
        dayHeader.className = 'day-header';
        if (isToday) dayHeader.classList.add('today');
        if (isSelected) dayHeader.classList.add('selected');

        dayHeader.innerHTML = `
            <span class="day-name">${day.toLocaleDateString('en-US', { weekday: 'long' })}</span>
            <span class="day-number">${day.getDate()}</span>
            <span class="day-date">${day.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
        `;
        weekHeader.appendChild(dayHeader);
    }

    // Build time column (00:00 to 23:00)
    const timeColumn = document.getElementById('weekTimeColumn');
    timeColumn.innerHTML = '';
    for (let hour = 0; hour < 24; hour++) {
        const timeSlot = document.createElement('div');
        timeSlot.className = 'time-slot';
        timeSlot.textContent = `${String(hour).padStart(2, '0')}:00`;
        timeColumn.appendChild(timeSlot);
    }

    // Build day columns with hour slots
    const weekGrid = document.getElementById('weekView');
    // Remove old day columns (keep only time column)
    const existingDayColumns = weekGrid.querySelectorAll('.day-column');
    existingDayColumns.forEach(col => col.remove());

    // Create day columns
    for (let i = 0; i < DAYS_PER_WEEK; i++) {
        const day = new Date(startOfWeek);
        day.setDate(startOfWeek.getDate() + i);
        const dateStr = day.toISOString().split('T')[0];

        const dayColumn = document.createElement('div');
        dayColumn.className = 'day-column';
        dayColumn.setAttribute('data-date', dateStr);

        // Add hour slots to this day
        for (let hour = 0; hour < HOURS_PER_DAY; hour++) {
            const hourSlot = document.createElement('div');
            hourSlot.className = 'hour-slot';
            hourSlot.setAttribute('data-hour', hour);
            hourSlot.setAttribute('data-date', dateStr);
            hourSlot.setAttribute('data-clickable', 'hour-slot');

            dayColumn.appendChild(hourSlot);
        }

        weekGrid.appendChild(dayColumn);
    }

    // Clear existing events
    document.querySelectorAll('.event-block').forEach(el => el.remove());

    // Set up event delegation (only once per container)
    setupWeekViewEventDelegation(weekGrid);

    // Render Google Calendar events
    calendarEvents.forEach(event => {
        const startDate = new Date(event.start);
        const endDate = new Date(event.end);

        const dateStr = event.start.split('T')[0];
        const dayColumn = document.querySelector(`.day-column[data-date="${dateStr}"]`);

        if (!dayColumn) return;

        const startHour = startDate.getHours();
        const hourSlot = dayColumn.querySelector(`.hour-slot[data-hour="${startHour}"]`);
        if (!hourSlot) return;

        const eventBlock = document.createElement('div');
        eventBlock.className = 'event-block calendar-event';
        eventBlock.setAttribute('data-event-id', event.id || Math.random());
        eventBlock.setAttribute('data-clickable', 'event');

        eventBlock.innerHTML = `
            <div class="event-time-range">
                ${formatTime(startDate)} - ${formatTime(endDate)}
            </div>
            <div class="event-title">${escapeHtml(event.title)}</div>
        `;

        eventBlock.style.cursor = 'pointer';
        
        // Store event data in map for later retrieval
        eventsDataMap.set(eventBlock.getAttribute('data-event-id'), event);

        hourSlot.appendChild(eventBlock);
    });

    // Render local tasks
    tasks.forEach(task => {
        if (!task.due_date) return;

        const [datePart, timePart] = task.due_date.split('T');
        const [year, month, day] = datePart.split('-').map(Number);
        const [hour, minute] = timePart.split(':').map(Number);

        const taskDate = new Date(year, month - 1, day, hour, minute);
        const dateStr = datePart;

        const dayColumn = document.querySelector(`.day-column[data-date="${dateStr}"]`);
        if (!dayColumn) return;

        const hourSlot = dayColumn.querySelector(`.hour-slot[data-hour="${hour}"]`);
        if (!hourSlot) return;

        const taskBlock = document.createElement('div');
        taskBlock.className = 'event-block task-block';
        taskBlock.classList.add(`status-${task.status}`);
        if (task.synced) taskBlock.classList.add('synced');
        taskBlock.setAttribute('data-task-id', task.id || Math.random());
        taskBlock.setAttribute('data-clickable', 'task');

        const categoryColor = getCategoryColor(task.category);
        taskBlock.style.borderLeftColor = categoryColor;
        taskBlock.style.backgroundColor = categoryColor + '25';

        const timeDiv = document.createElement('div');
        timeDiv.className = 'event-time-range';
        timeDiv.textContent = formatTime(taskDate);

        const titleDiv = document.createElement('div');
        titleDiv.className = 'event-title';
        titleDiv.textContent = task.title;

        taskBlock.appendChild(timeDiv);
        taskBlock.appendChild(titleDiv);

        taskBlock.style.cursor = 'pointer';
        
        // Store task data in map for later retrieval
        tasksDataMap.set(taskBlock.getAttribute('data-task-id'), task);

        hourSlot.appendChild(taskBlock);
    });

    // Adjust hour slot heights based on number of events
    const grid = document.querySelector('.week-calendar-grid');
    const gridTimeColumn = grid.querySelector('.time-column');
    const timeSlots = Array.from(gridTimeColumn.querySelectorAll('.time-slot'));

    const maxTasksPerHour = new Array(HOURS_PER_DAY).fill(0);

    document.querySelectorAll('.day-column').forEach(dayColumn => {
        dayColumn.querySelectorAll('.hour-slot').forEach(hourSlot => {
            const hour = parseInt(hourSlot.getAttribute('data-hour'));
            const tasksInSlot = hourSlot.querySelectorAll('.event-block').length;
            maxTasksPerHour[hour] = Math.max(maxTasksPerHour[hour], tasksInSlot);
        });
    });

    maxTasksPerHour.forEach((taskCount, hour) => {
        const newHeight = taskCount > 1 ? (taskCount * HOUR_SLOT_HEIGHT) : HOUR_SLOT_HEIGHT;

        if (timeSlots[hour]) {
            timeSlots[hour].style.height = `${newHeight}px`;
            timeSlots[hour].style.minHeight = `${newHeight}px`;
        }

        document.querySelectorAll(`.hour-slot[data-hour="${hour}"]`).forEach(slot => {
            slot.style.height = `${newHeight}px`;
            slot.style.minHeight = `${newHeight}px`;
        });
    });
}

/**
 * Setup event delegation for week view interactions
 * Prevents memory leaks from repeated event listener creation
 * @param {HTMLElement} weekGrid - The week grid container
 */
let weekViewDelegationSetup = false;
function setupWeekViewEventDelegation(weekGrid) {
    // Only set up once to avoid duplicate listeners
    if (weekViewDelegationSetup) return;
    weekViewDelegationSetup = true;
    
    weekGrid.addEventListener('click', function(e) {
        // Handle hour slot clicks (for adding events)
        const hourSlot = e.target.closest('[data-clickable="hour-slot"]');
        if (hourSlot && !e.target.closest('.event-block')) {
            const dateStr = hourSlot.getAttribute('data-date');
            const hour = parseInt(hourSlot.getAttribute('data-hour'));
            const eventModal = document.getElementById('eventModal');
            if (eventModal) {
                eventModal.classList.add('active');
                document.getElementById('eventDate').value = dateStr;
                document.getElementById('eventStartTime').value = `${String(hour).padStart(2, '0')}:00`;
                document.getElementById('eventEndTime').value = `${String(hour + 1).padStart(2, '0')}:00`;
            }
            return;
        }
        
        // Handle event block clicks
        const eventBlock = e.target.closest('[data-clickable="event"]');
        if (eventBlock) {
            e.stopPropagation();
            const eventId = eventBlock.getAttribute('data-event-id');
            const event = eventsDataMap.get(eventId);
            if (event) {
                showCalendarEventDetails(event);
            }
            return;
        }
        
        // Handle task block clicks
        const taskBlock = e.target.closest('[data-clickable="task"]');
        if (taskBlock) {
            e.stopPropagation();
            const taskId = taskBlock.getAttribute('data-task-id');
            const task = tasksDataMap.get(taskId);
            if (task) {
                showTaskDetails(task);
            }
            return;
        }
    });
}
