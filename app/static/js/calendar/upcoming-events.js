// =============================================================================
// UPCOMING EVENTS
// Renders the upcoming events list in the sidebar
// =============================================================================

import { escapeHtml, getCategoryColor } from './utils.js';
import { UPCOMING_EVENTS_DAYS_AHEAD } from './constants.js';

/**
 * Render upcoming events for the next few days
 * @param {Object[]} upcomingCalendarEvents - Calendar events starting from today
 * @param {Object[]} upcomingTasks - Tasks starting from today
 */
export function renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks) {
    const upcomingContainer = document.getElementById('upcomingEventsList');
    if (!upcomingContainer) return;

    // Get current date (start of today) and upcoming days from now (end of day)
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const weekFromNow = new Date(now);
    weekFromNow.setDate(weekFromNow.getDate() + UPCOMING_EVENTS_DAYS_AHEAD);
    weekFromNow.setHours(23, 59, 59, 999);

    // Collect all events (calendar + tasks) in the upcoming days
    const upcomingEvents = [];

    // Add Google Calendar events
    if (Array.isArray(upcomingCalendarEvents)) {
        upcomingCalendarEvents.forEach(event => {
            if (event.start) {
                const eventDate = new Date(event.start);
                if (eventDate >= now && eventDate <= weekFromNow) {
                    upcomingEvents.push({
                        title: event.title || 'Untitled Event',
                        start: event.start,
                        end: event.end,
                        location: event.location || '',
                        type: 'calendar',
                        date: eventDate
                    });
                }
            }
        });
    }

    // Add local tasks
    if (Array.isArray(upcomingTasks)) {
        upcomingTasks.forEach(task => {
            if (task.due_date) {
                const taskDate = new Date(task.due_date);
                if (taskDate >= now && taskDate <= weekFromNow) {
                    upcomingEvents.push({
                        title: task.title || 'Untitled Task',
                        start: task.due_date,
                        end: null,
                        location: '',
                        type: 'task',
                        status: task.status,
                        category: task.category,
                        date: taskDate
                    });
                }
            }
        });
    }

    // Sort by start time
    upcomingEvents.sort((a, b) => a.date - b.date);

    // Render events
    if (upcomingEvents.length === 0) {
        upcomingContainer.innerHTML = `
            <p class="no-events-message">
                <i class="fas fa-calendar-check"></i>
                No upcoming events in the next ${UPCOMING_EVENTS_DAYS_AHEAD} days
            </p>
        `;
    } else {
        upcomingContainer.innerHTML = upcomingEvents.map(event => {
            const eventDate = event.date;
            const dateOptions = { weekday: 'short', month: 'short', day: 'numeric' };
            const dateStr = eventDate.toLocaleDateString('en-US', dateOptions);

            let timeStr = 'All Day';
            if (event.start.includes('T')) {
                const timeOptions = { hour: '2-digit', minute: '2-digit' };
                timeStr = eventDate.toLocaleTimeString('en-US', timeOptions);
            }

            const typeClass = event.type === 'task' ? 'task-event' : 'calendar-event';
            const categoryColor = event.category ? getCategoryColor(event.category) : '#3498db';

            return `
                <div class="upcoming-event-card ${typeClass}" style="border-left-color: ${categoryColor};">
                    <div class="event-time">
                        <span class="event-date">${dateStr}</span>
                        <span class="event-hour">${timeStr}</span>
                    </div>
                    <div class="event-details">
                        <h4>${escapeHtml(event.title)}</h4>
                        ${event.location ? `
                            <p class="event-location">
                                <i class="fas fa-map-marker-alt"></i> ${escapeHtml(event.location)}
                            </p>
                        ` : ''}
                        ${event.type === 'task' && event.status ? `
                            <span class="event-status status-${event.status}">${event.status}</span>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }
}
