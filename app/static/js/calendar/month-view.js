// =============================================================================
// MONTH VIEW RENDERER
// Renders the monthly calendar grid with events
// =============================================================================

import { showCalendarEventDetails, showTaskDetails } from './event-modals.js';
import { MAX_EVENTS_IN_MONTH_VIEW, DAYS_PER_WEEK } from './constants.js';

/**
 * Render month view calendar
 * @param {number} month - Current month (1-12)
 * @param {number} year - Current year
 * @param {Date} currentDate - Currently selected date
 * @param {Object[]} calendarEvents - Array of calendar events
 * @param {Object[]} tasks - Array of tasks
 */
export function renderMonthView(month, year, currentDate, calendarEvents, tasks) {
    const monthDaysGrid = document.getElementById('monthDaysGrid');
    if (!monthDaysGrid) return;
    
    monthDaysGrid.innerHTML = '';

    const firstDay = new Date(year, month - 1, 1);
    const lastDay = new Date(year, month, 0);

    let firstDayOfWeek = firstDay.getDay();
    firstDayOfWeek = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1;

    const daysInMonth = lastDay.getDate();
    const prevMonth = month === 1 ? 12 : month - 1;
    const prevMonthYear = month === 1 ? year - 1 : year;
    const daysInPrevMonth = new Date(prevMonthYear, prevMonth, 0).getDate();

    // Organize events by date
    const eventsByDate = {};
    calendarEvents.forEach(event => {
        const eventDateStr = event.start.split('T')[0];
        if (!eventsByDate[eventDateStr]) eventsByDate[eventDateStr] = [];
        eventsByDate[eventDateStr].push({ ...event, type: 'calendar' });
    });

    tasks.forEach(task => {
        if (task.due_date) {
            const taskDateStr = task.due_date.split('T')[0];
            if (!eventsByDate[taskDateStr]) eventsByDate[taskDateStr] = [];
            eventsByDate[taskDateStr].push({ ...task, type: 'task' });
        }
    });

    // Previous month days
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
        const day = daysInPrevMonth - i;
        const cell = document.createElement('div');
        cell.className = 'month-day-cell other-month';
        cell.textContent = day;
        monthDaysGrid.appendChild(cell);
    }

    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const cell = document.createElement('div');
        cell.className = 'month-day-cell';

        const today = new Date();
        if (year === today.getFullYear() &&
            month === (today.getMonth() + 1) &&
            day === today.getDate()) {
            cell.classList.add('today');
        }

        if (currentDate.toDateString() === new Date(year, month - 1, day).toDateString()) {
            cell.classList.add('selected');
        }

        const dayNumber = document.createElement('div');
        dayNumber.className = 'month-day-number';
        dayNumber.textContent = day;
        cell.appendChild(dayNumber);

        const eventsContainer = document.createElement('div');
        eventsContainer.className = 'month-events';

        if (eventsByDate[dateStr]) {
            const dayEvents = eventsByDate[dateStr];
            const maxDisplay = MAX_EVENTS_IN_MONTH_VIEW;

            dayEvents.slice(0, maxDisplay).forEach(event => {
                const eventItem = document.createElement('div');
                eventItem.className = `month-event-item ${event.type}-event`;
                eventItem.textContent = event.title;

                eventItem.addEventListener('click', function (e) {
                    e.stopPropagation();
                    if (event.type === 'calendar') {
                        showCalendarEventDetails(event);
                    } else {
                        showTaskDetails(event);
                    }
                });

                eventsContainer.appendChild(eventItem);
            });

            if (dayEvents.length > maxDisplay) {
                const moreItem = document.createElement('div');
                moreItem.className = 'month-event-more';
                moreItem.textContent = `+${dayEvents.length - maxDisplay} more`;
                moreItem.addEventListener('click', function (e) {
                    e.stopPropagation();
                    alert(`${dayEvents.length} events on this day. Click individual events to view details.`);
                });
                eventsContainer.appendChild(moreItem);
            }
        }

        cell.appendChild(eventsContainer);
        cell.addEventListener('click', function () {
            // Could navigate to day view
        });

        monthDaysGrid.appendChild(cell);
    }

    // Next month days
    const totalCells = Math.ceil((firstDayOfWeek + daysInMonth) / DAYS_PER_WEEK) * DAYS_PER_WEEK;
    const nextDays = totalCells - (firstDayOfWeek + daysInMonth);
    for (let day = 1; day <= nextDays; day++) {
        const cell = document.createElement('div');
        cell.className = 'month-day-cell other-month';
        cell.textContent = day;
        monthDaysGrid.appendChild(cell);
    }
}
