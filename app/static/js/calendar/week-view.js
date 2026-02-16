// =============================================================================
// WEEK VIEW RENDERER
// Renders the weekly calendar grid with events
// =============================================================================

import { formatTime, getDayNames } from './utils.js';
import { showCalendarEventDetails, showTaskDetails } from './event-modals.js';
import { getCategoryColor } from './utils.js';

/**
 * Render week view calendar
 * @param {Date} currentDate - Currently selected date
 * @param {Object[]} calendarEvents - Array of calendar events
 * @param {Object[]} tasks - Array of tasks
 */
export function renderWeekView(currentDate, calendarEvents, tasks) {
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

    // Generate 7 day headers (Monday to Sunday)
    for (let i = 0; i < 7; i++) {
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

    // Create 7 day columns
    for (let i = 0; i < 7; i++) {
        const day = new Date(startOfWeek);
        day.setDate(startOfWeek.getDate() + i);
        const dateStr = day.toISOString().split('T')[0];

        const dayColumn = document.createElement('div');
        dayColumn.className = 'day-column';
        dayColumn.setAttribute('data-date', dateStr);

        // Add 24 hour slots to this day
        for (let hour = 0; hour < 24; hour++) {
            const hourSlot = document.createElement('div');
            hourSlot.className = 'hour-slot';
            hourSlot.setAttribute('data-hour', hour);

            // Add click handler for adding events
            hourSlot.addEventListener('click', function () {
                const eventModal = document.getElementById('eventModal');
                if (eventModal) {
                    eventModal.classList.add('active');
                    document.getElementById('eventDate').value = dateStr;
                    document.getElementById('eventStartTime').value = `${String(hour).padStart(2, '0')}:00`;
                    document.getElementById('eventEndTime').value = `${String(hour + 1).padStart(2, '0')}:00`;
                }
            });

            dayColumn.appendChild(hourSlot);
        }

        weekGrid.appendChild(dayColumn);
    }

    // Clear existing events
    document.querySelectorAll('.event-block').forEach(el => el.remove());

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

        eventBlock.innerHTML = `
            <div class="event-time-range">
                ${formatTime(startDate)} - ${formatTime(endDate)}
            </div>
            <div class="event-title">${event.title}</div>
        `;

        eventBlock.style.cursor = 'pointer';
        eventBlock.addEventListener('click', function (e) {
            e.stopPropagation();
            showCalendarEventDetails(event);
        });

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
        taskBlock.addEventListener('click', function (e) {
            e.stopPropagation();
            showTaskDetails(task);
        });

        hourSlot.appendChild(taskBlock);
    });

    // Adjust hour slot heights based on number of events
    const grid = document.querySelector('.week-calendar-grid');
    const gridTimeColumn = grid.querySelector('.time-column');
    const timeSlots = Array.from(gridTimeColumn.querySelectorAll('.time-slot'));

    const maxTasksPerHour = new Array(24).fill(0);

    document.querySelectorAll('.day-column').forEach(dayColumn => {
        dayColumn.querySelectorAll('.hour-slot').forEach(hourSlot => {
            const hour = parseInt(hourSlot.getAttribute('data-hour'));
            const tasksInSlot = hourSlot.querySelectorAll('.event-block').length;
            maxTasksPerHour[hour] = Math.max(maxTasksPerHour[hour], tasksInSlot);
        });
    });

    maxTasksPerHour.forEach((taskCount, hour) => {
        const newHeight = taskCount > 1 ? (taskCount * 60) : 60;

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
