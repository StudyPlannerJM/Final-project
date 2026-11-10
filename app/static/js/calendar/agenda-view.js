// =============================================================================
// AGENDA VIEW
// The next few days as a simple list grouped by day. Default view on phones.
// =============================================================================

import { escapeHtml, getCategoryColor } from './utils.js';
import { showCalendarEventDetails, showTaskDetails } from './event-modals.js';
import { UPCOMING_EVENTS_DAYS_AHEAD } from './constants.js';

const STATUS_LABELS = { todo: 'To-Do', doing: 'Doing', done: 'Done' };

/** Local calendar-day key (YYYY-MM-DD) so items group by the user's own day. */
function dayKey(date) {
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${date.getFullYear()}-${month}-${day}`;
}

function dayHeading(date, today) {
    const diffDays = Math.round((new Date(date).setHours(0, 0, 0, 0) - today.getTime()) / 86400000);
    const long = date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
    if (diffDays === 0) return { label: 'Today', detail: long };
    if (diffDays === 1) return { label: 'Tomorrow', detail: long };
    return { label: date.toLocaleDateString('en-US', { weekday: 'long' }),
             detail: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) };
}

/** Normalise calendar events and tasks into one sorted list of agenda items. */
function collectItems(calendarEvents, tasks, rangeStart, rangeEnd) {
    const items = [];

    (Array.isArray(calendarEvents) ? calendarEvents : []).forEach((event) => {
        if (!event.start) return;
        const date = new Date(event.start);
        if (Number.isNaN(date.getTime()) || date < rangeStart || date > rangeEnd) return;
        items.push({
            type: 'calendar',
            date,
            allDay: !String(event.start).includes('T'),
            title: event.title || 'Untitled event',
            source: event
        });
    });

    (Array.isArray(tasks) ? tasks : []).forEach((task) => {
        if (!task.due_date) return;
        const date = new Date(task.due_date);
        if (Number.isNaN(date.getTime()) || date < rangeStart || date > rangeEnd) return;
        items.push({
            type: 'task',
            date,
            allDay: false,
            title: task.title || 'Untitled task',
            source: task
        });
    });

    // All-day items first within a day, then by time
    items.sort((a, b) => {
        const sameDay = dayKey(a.date) === dayKey(b.date);
        if (sameDay && a.allDay !== b.allDay) return a.allDay ? -1 : 1;
        return a.date - b.date;
    });
    return items;
}

function itemHtml(item, index) {
    const time = item.allDay
        ? 'All day'
        : item.date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    const isTask = item.type === 'task';
    const color = isTask && item.source.category ? getCategoryColor(item.source.category) : null;
    const status = isTask && item.source.status ? item.source.status : null;
    const location = !isTask && item.source.location ? item.source.location : '';

    return `
        <li>
            <button type="button" class="agenda-item agenda-item--${item.type}${status === 'done' ? ' is-done' : ''}"
                data-agenda-index="${index}"${color ? ` style="--agenda-color: ${escapeHtml(color)}"` : ''}>
                <span class="agenda-item__time">${escapeHtml(time)}</span>
                <span class="agenda-item__body">
                    <span class="agenda-item__title">${escapeHtml(item.title)}</span>
                    <span class="agenda-item__meta">
                        <i class="fas ${isTask ? 'fa-list-check' : 'fa-calendar'}" aria-hidden="true"></i>
                        ${isTask ? 'Task' : 'Event'}${status ? ` · ${escapeHtml(STATUS_LABELS[status] || status)}` : ''}${location ? ` · ${escapeHtml(location)}` : ''}
                    </span>
                </span>
                <i class="fas fa-chevron-right agenda-item__chevron" aria-hidden="true"></i>
            </button>
        </li>`;
}

/**
 * Render the agenda list.
 * @param {Object[]} calendarEvents - Google Calendar events in the range
 * @param {Object[]} tasks - Tasks with due dates in the range
 */
export function renderAgendaView(calendarEvents, tasks) {
    const container = document.getElementById('agendaView');
    if (!container) return;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const rangeEnd = new Date(today);
    rangeEnd.setDate(rangeEnd.getDate() + UPCOMING_EVENTS_DAYS_AHEAD);
    rangeEnd.setHours(23, 59, 59, 999);

    const items = collectItems(calendarEvents, tasks, today, rangeEnd);

    if (items.length === 0) {
        container.innerHTML = `
            <div class="agenda-empty">
                <i class="fas fa-calendar-check" aria-hidden="true"></i>
                <p class="agenda-empty__title">Nothing scheduled</p>
                <p>No events or task deadlines in the next ${UPCOMING_EVENTS_DAYS_AHEAD} days.</p>
            </div>`;
        return;
    }

    const groups = new Map();
    items.forEach((item, index) => {
        const key = dayKey(item.date);
        if (!groups.has(key)) groups.set(key, { date: item.date, html: [] });
        groups.get(key).html.push(itemHtml(item, index));
    });

    container.innerHTML = Array.from(groups.values()).map((group) => {
        const heading = dayHeading(group.date, today);
        return `
            <section class="agenda-day">
                <h3 class="agenda-day__heading">
                    <span>${escapeHtml(heading.label)}</span>
                    <span class="agenda-day__date">${escapeHtml(heading.detail)}</span>
                </h3>
                <ul class="agenda-list">${group.html.join('')}</ul>
            </section>`;
    }).join('');

    container.querySelectorAll('.agenda-item').forEach((button) => {
        button.addEventListener('click', () => {
            const item = items[Number(button.dataset.agendaIndex)];
            if (!item) return;
            if (item.type === 'task') {
                showTaskDetails(item.source);
            } else {
                showCalendarEventDetails(item.source);
            }
        });
    });
}
