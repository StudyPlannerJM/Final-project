// =============================================================================
// DAY VIEW RENDERER
// Renders the single day calendar view with hourly events
// =============================================================================

import { formatTime, escapeHtml, localDateString } from './utils.js';
import { showCalendarEventDetails, showTaskDetails } from './event-modals.js';
import { getCategoryColor } from './utils.js';
import { HOURS_PER_DAY } from './constants.js';

// Store events and tasks data for event delegation
let dayEventsDataMap = new Map();
let dayTasksDataMap = new Map();

/**
 * Render day view calendar
 * @param {Date} currentDate - Currently selected date
 * @param {Object[]} calendarEvents - Array of calendar events
 * @param {Object[]} tasks - Array of tasks
 */
export function renderDayView(currentDate, calendarEvents, tasks) {
    const dayEventsColumn = document.getElementById('dayEventsColumn');
    if (!dayEventsColumn) return;
    
    // Clear previous data maps
    dayEventsDataMap.clear();
    dayTasksDataMap.clear();

    const dateStr = localDateString(currentDate);
    dayEventsColumn.setAttribute('data-date', dateStr);

    // Update day header
    const dayHeader = document.getElementById('dayViewDateHeader');
    if (dayHeader) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const formattedDate = currentDate.toLocaleDateString('en-US', options);

        const today = new Date();
        const isToday = currentDate.toDateString() === today.toDateString();

        dayHeader.innerHTML = `
            ${formattedDate}
            ${isToday ? '<span class="today-badge">TODAY</span>' : ''}
        `;
    }

    // Build time column
    const timeColumn = document.getElementById('dayTimeColumn');
    if (timeColumn) {
        timeColumn.innerHTML = '';
        for (let hour = 0; hour < HOURS_PER_DAY; hour++) {
            const timeSlot = document.createElement('div');
            timeSlot.className = 'time-slot';
            timeSlot.textContent = `${String(hour).padStart(2, '0')}:00`;
            timeColumn.appendChild(timeSlot);
        }
    }

    // Build hour slots for the day
    dayEventsColumn.innerHTML = '';
    for (let hour = 0; hour < 24; hour++) {
        const hourSlot = document.createElement('div');
        hourSlot.className = 'hour-slot';
        hourSlot.setAttribute('data-hour', hour);
        hourSlot.setAttribute('data-date', dateStr);
        hourSlot.setAttribute('data-clickable', 'hour-slot');

        dayEventsColumn.appendChild(hourSlot);
    }
    
    // Set up event delegation (only once per container)
    setupDayViewEventDelegation(dayEventsColumn);

    // Render calendar events for this day
    calendarEvents.forEach(event => {
        const eventDateStr = event.start.split('T')[0];
        if (eventDateStr !== dateStr) return;

        const startDate = new Date(event.start);
        const endDate = new Date(event.end);
        const startHour = startDate.getHours();

        const hourSlot = dayEventsColumn.querySelector(`.hour-slot[data-hour="${startHour}"]`);
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
        dayEventsDataMap.set(eventBlock.getAttribute('data-event-id'), event);

        hourSlot.appendChild(eventBlock);
    });

    // Render tasks for this day
    tasks.forEach(task => {
        if (!task.due_date) return;

        const [taskDatePart, taskTimePart] = task.due_date.split('T');
        if (taskDatePart !== dateStr) return;

        const [year, month, day] = taskDatePart.split('-').map(Number);
        const [hour, minute] = taskTimePart.split(':').map(Number);
        const taskDate = new Date(year, month - 1, day, hour, minute);

        const hourSlot = dayEventsColumn.querySelector(`.hour-slot[data-hour="${hour}"]`);
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

        taskBlock.innerHTML = `
            <div class="event-time-range">${formatTime(taskDate)}</div>
            <div class="event-title">${escapeHtml(task.title)}</div>
        `;

        taskBlock.style.cursor = 'pointer';
        
        // Store task data in map for later retrieval
        dayTasksDataMap.set(taskBlock.getAttribute('data-task-id'), task);

        hourSlot.appendChild(taskBlock);
    });

    // Adjust heights for slots with multiple events
    dayEventsColumn.querySelectorAll('.hour-slot').forEach(slot => {
        const tasksInSlot = slot.querySelectorAll('.event-block').length;
        if (tasksInSlot > 1) {
            const newHeight = tasksInSlot * 60;
            slot.style.height = `${newHeight}px`;
            slot.style.minHeight = `${newHeight}px`;

            const hour = parseInt(slot.getAttribute('data-hour'));
            const timeSlot = timeColumn?.querySelectorAll('.time-slot')[hour];
            if (timeSlot) {
                timeSlot.style.height = `${newHeight}px`;
                timeSlot.style.minHeight = `${newHeight}px`;
            }
        }
    });
}

/**
 * Setup event delegation for day view interactions
 * Prevents memory leaks from repeated event listener creation
 * @param {HTMLElement} dayEventsColumn - The day events container
 */
let dayViewDelegationSetup = false;
function setupDayViewEventDelegation(dayEventsColumn) {
    // Only set up once to avoid duplicate listeners
    if (dayViewDelegationSetup) return;
    dayViewDelegationSetup = true;
    
    dayEventsColumn.addEventListener('click', function(e) {
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
            const event = dayEventsDataMap.get(eventId);
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
            const task = dayTasksDataMap.get(taskId);
            if (task) {
                showTaskDetails(task);
            }
            return;
        }
    });
}
