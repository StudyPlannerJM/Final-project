// =============================================================================
// MINI CALENDAR
// Renders the small month calendar for date navigation
// =============================================================================

import { getMonthNames } from './utils.js';

/**
 * Update mini calendar header with current month/year
 * @param {number} month - Month number (1-12)
 * @param {number} year - Year
 */
export function updateMiniCalendarHeader(month, year) {
    const monthNames = getMonthNames();
    const headerEl = document.getElementById('currentMonthYear');
    if (headerEl) {
        headerEl.textContent = `${monthNames[month - 1]} ${year}`;
    }
}

/**
 * Render the mini calendar
 * @param {number} month - Current month (1-12)
 * @param {number} year - Current year
 * @param {Date} currentDate - Currently selected date
 * @param {Object[]} calendarEvents - Array of calendar events
 * @param {Object[]} tasks - Array of tasks
 * @param {Function} onDateClick - Callback when a date is clicked
 */
export function renderMiniCalendar(month, year, currentDate, calendarEvents, tasks, onDateClick) {
    const calendarDays = document.getElementById('calendarDays');
    if (!calendarDays) return;

    const firstDay = new Date(year, month - 1, 1);
    const lastDay = new Date(year, month, 0);
    const prevLastDay = new Date(year, month - 1, 0);

    const firstDayIndex = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
    const lastDayDate = lastDay.getDate();
    const prevLastDayDate = prevLastDay.getDate();

    // Calculate event counts for this month
    const monthEvents = {};
    calendarEvents.forEach(event => {
        const eventDate = event.start.split('T')[0];
        if (!monthEvents[eventDate]) monthEvents[eventDate] = 0;
        monthEvents[eventDate]++;
    });
    tasks.forEach(task => {
        if (task.due_date) {
            const taskDate = task.due_date.split('T')[0];
            if (!monthEvents[taskDate]) monthEvents[taskDate] = 0;
            monthEvents[taskDate]++;
        }
    });

    // Check if we're viewing the same month as the selected date
    const viewingSelectedMonth = currentDate.getMonth() + 1 === month && currentDate.getFullYear() === year;

    let daysHTML = '';

    // Previous month days
    for (let i = firstDayIndex; i > 0; i--) {
        daysHTML += `<div class="calendar-day other-month">${prevLastDayDate - i + 1}</div>`;
    }

    // Current month days
    for (let day = 1; day <= lastDayDate; day++) {
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const isSelected = viewingSelectedMonth && currentDate.getDate() === day;
        const hasEvents = monthEvents[dateStr] && monthEvents[dateStr] > 0;

        const classes = ['calendar-day'];
        if (isSelected) classes.push('selected');
        if (hasEvents) classes.push('has-events');

        daysHTML += `<div class="${classes.join(' ')}" data-date="${dateStr}">${day}</div>`;
    }

    // Next month days
    const totalCells = Math.ceil((firstDayIndex + lastDayDate) / 7) * 7;
    const nextDays = totalCells - (firstDayIndex + lastDayDate);
    for (let day = 1; day <= nextDays; day++) {
        daysHTML += `<div class="calendar-day other-month">${day}</div>`;
    }

    calendarDays.innerHTML = daysHTML;

    // Add click handlers for date selection
    calendarDays.querySelectorAll('.calendar-day:not(.other-month)').forEach(dayEl => {
        dayEl.addEventListener('click', function () {
            const selectedDate = this.getAttribute('data-date');
            if (selectedDate && onDateClick) {
                onDateClick(new Date(selectedDate));
            }
        });
    });
}
