// =============================================================================
// MAIN SCHEDULE MODULE
// Orchestrates calendar functionality using modular components
// =============================================================================

// Import calendar modules
import { renderWeekView } from './calendar/week-view.js';
import { renderDayView } from './calendar/day-view.js';
import { renderMonthView } from './calendar/month-view.js';
import { renderMiniCalendar, updateMiniCalendarHeader } from './calendar/mini-calendar.js';
import { renderUpcomingEvents } from './calendar/upcoming-events.js';
import { showCalendarEventDetails, showTaskDetails, closeTaskDetailsModal } from './calendar/event-modals.js';
import { getMonthNames } from './calendar/utils.js';
import { MONTHS_PER_YEAR, DAYS_PER_WEEK } from './calendar/constants.js';

// =============================================================================
// GLOBAL STATE
// =============================================================================
let calendarEvents = [];
let tasks = [];
let upcomingCalendarEvents = [];
let upcomingTasks = [];
let currentDate;
let currentMonth;
let currentYear;
let activeView = 'week';
let calendarConnected = false;
let currentTaskId = null;
let currentEventId = null;
let isGoogleCalendarEvent = false;

// =============================================================================
// DOM CACHE
// Cache frequently accessed DOM elements for better performance
// =============================================================================
const domCache = {};

/**
 * Initialize DOM element cache
 * Call once during page load to store references to frequently accessed elements
 */
function initializeDOMCache() {
    // View containers
    domCache.weekView = document.getElementById('weekView');
    domCache.monthView = document.getElementById('monthView');
    domCache.dayView = document.getElementById('dayView');
    domCache.weekDaysHeader = document.querySelector('.week-days-header');
    
    // Navigation buttons
    domCache.prevWeek = document.getElementById('prevWeek');
    domCache.nextWeek = document.getElementById('nextWeek');
    domCache.todayBtn = document.getElementById('todayBtn');
    domCache.prevMonth = document.getElementById('prevMonth');
    domCache.nextMonth = document.getElementById('nextMonth');
    
    // Headers
    domCache.mainCalendarHeader = document.getElementById('mainCalendarHeader');
    
    // Event modal elements
    domCache.eventModal = document.getElementById('eventModal');
    domCache.addEventBtn = document.getElementById('addEventBtn');
    domCache.closeModal = document.getElementById('closeModal');
    domCache.cancelBtn = document.getElementById('cancelBtn');
    domCache.eventForm = document.getElementById('eventForm');
    domCache.eventDate = document.getElementById('eventDate');
    
    // Task details modal elements
    domCache.taskDetailsModal = document.getElementById('taskDetailsModal');
    domCache.closeTaskDetails = document.getElementById('closeTaskDetails');
    domCache.closeTaskDetailsBtn = document.getElementById('closeTaskDetailsBtn');
    domCache.editTaskBtn = document.getElementById('editTaskBtn');
    
    // Initial data
    domCache.initialDataElement = document.getElementById('initialData');
}

// =============================================================================
// DATA FETCHING
// =============================================================================

async function fetchCalendarData(date, view) {
    const dateStr = date.toISOString().split('T')[0];

    try {
        const response = await fetch(`/calendar/api/events?date=${dateStr}&view=${view}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            console.error('Failed to fetch calendar data:', data.error);
            showNotification('Failed to load calendar data: ' + (data.error || 'Unknown error'), 'error');
            return false;
        }

        calendarEvents = data.calendarEvents || [];
        tasks = data.tasks || [];
        calendarConnected = data.calendarConnected || false;
        currentMonth = data.currentMonth || date.getMonth() + 1;
        currentYear = data.currentYear || date.getFullYear();

        return data;
    } catch (error) {
        console.error('Error fetching calendar data:', error);
        showNotification('Error loading calendar. Please refresh the page.', 'error');
        return false;
    }
}

async function fetchUpcomingEvents() {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];

    try {
        const response = await fetch(`/calendar/api/events?date=${todayStr}&view=upcoming`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            upcomingCalendarEvents = data.calendarEvents || [];
            upcomingTasks = data.tasks || [];
        }
    } catch (error) {
        console.error('Error fetching upcoming events:', error);
    }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Show a branded BrainDump confirm modal.
 * Returns a Promise<boolean> — true if the user confirmed, false if cancelled.
 * @param {string} title       - Modal heading
 * @param {string} message     - Body message
 * @param {string} iconClass   - FontAwesome icon class (e.g. 'fas fa-calendar-times')
 * @param {string} confirmText - Label for the confirm button
 * @param {string} confirmColor - Background colour for the confirm button
 */
function showStudyConfirmModal(
    title       = 'Confirm Action',
    message     = 'Are you sure you want to proceed?',
    iconClass   = 'fas fa-exclamation-triangle',
    confirmText = 'Confirm',
    confirmColor = '#e53935'
) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.style.cssText = [
            'position:fixed', 'inset:0', 'background:rgba(0,0,0,0.55)',
            'display:flex', 'align-items:center', 'justify-content:center',
            'z-index:9999', 'animation:fadeIn .15s ease'
        ].join(';');

        overlay.innerHTML = `
            <div style="background:var(--card-bg,#fff);border-radius:14px;padding:2rem 2.25rem;
                        max-width:420px;width:90%;box-shadow:0 10px 40px rgba(0,0,0,.25);
                        text-align:center;">
                <div style="font-size:2.75rem;margin-bottom:.75rem;color:${confirmColor};">
                    <i class="${iconClass}"></i>
                </div>
                <h3 style="margin:0 0 .5rem;font-size:1.15rem;color:var(--text-color,#1a1a2e);">
                    ${title}
                </h3>
                <p style="margin:0 0 1.5rem;color:var(--muted-color,#666);font-size:.93rem;line-height:1.5;">
                    ${message}
                </p>
                <div style="display:flex;gap:.75rem;justify-content:center;">
                    <button id="scmCancel"
                        style="padding:.55rem 1.4rem;border-radius:8px;
                               border:1px solid var(--border-color,#ddd);
                               background:var(--card-bg,#fff);
                               color:var(--text-color,#333);
                               cursor:pointer;font-size:.88rem;">
                        Cancel
                    </button>
                    <button id="scmConfirm"
                        style="padding:.55rem 1.4rem;border-radius:8px;border:none;
                               background:${confirmColor};color:#fff;
                               cursor:pointer;font-size:.88rem;font-weight:600;">
                        ${confirmText}
                    </button>
                </div>
            </div>`;

        document.body.appendChild(overlay);

        const cleanup = (result) => {
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity .12s ease';
            setTimeout(() => { document.body.removeChild(overlay); resolve(result); }, 120);
        };

        overlay.querySelector('#scmConfirm').addEventListener('click', () => cleanup(true));
        overlay.querySelector('#scmCancel').addEventListener('click',  () => cleanup(false));
        overlay.addEventListener('click', (e) => { if (e.target === overlay) cleanup(false); });
    });
}

/**
 * Show a notification message to the user
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', 'info'
 */
function showNotification(message, type = 'info') {
    // TODO: Replace with a proper toast notification system
    // For now, using alert for user feedback
    alert(message);
}

/**
 * Refresh calendar view after data changes
 */
async function refreshCalendarView() {
    const [data, _] = await Promise.all([
        fetchCalendarData(currentDate, activeView),
        fetchUpcomingEvents()
    ]);
    
    if (data) {
        renderCurrentView();
        renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);
        updateMiniCalendarHeader(currentMonth, currentYear);
        updateMainCalendarHeader();
    }
}

/**
 * Change the current month by delta
 * @param {number} delta - Number of months to change (+1 or -1)
 * @param {boolean} updateMainView - Whether to update main calendar view
 */
async function changeMonth(delta, updateMainView = false) {
    currentMonth += delta;
    
    if (currentMonth < 1) {
        currentMonth = MONTHS_PER_YEAR;
        currentYear--;
    } else if (currentMonth > MONTHS_PER_YEAR) {
        currentMonth = 1;
        currentYear++;
    }
    
    const maxDayInMonth = new Date(currentYear, currentMonth, 0).getDate();
    const newDay = Math.min(currentDate.getDate(), maxDayInMonth);
    currentDate = new Date(currentYear, currentMonth - 1, newDay);
    
    updateMiniCalendarHeader(currentMonth, currentYear);
    renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);
    
    if (updateMainView) {
        const data = await fetchCalendarData(currentDate, 'month');
        if (data) {
            renderMonthView(currentMonth, currentYear, currentDate, calendarEvents, tasks);
            updateMainCalendarHeader();
        }
    }
}

// =============================================================================
// NAVIGATION
// =============================================================================

async function navigateToDate(date, view = null) {
    const viewParam = view || activeView;

    currentDate = new Date(date);
    currentMonth = currentDate.getMonth() + 1;
    currentYear = currentDate.getFullYear();

    const [data, _] = await Promise.all([
        fetchCalendarData(currentDate, viewParam),
        fetchUpcomingEvents()
    ]);

    if (data) {
        const dateStr = currentDate.toISOString().split('T')[0];
        const newUrl = `/schedule?date=${dateStr}&view=${viewParam}`;
        window.history.pushState({ date: dateStr, view: viewParam }, '', newUrl);

        renderCurrentView();
        renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);
        updateMiniCalendarHeader(currentMonth, currentYear);
        updateMainCalendarHeader();
    }
}

// =============================================================================
// VIEW RENDERING
// =============================================================================

function renderCurrentView() {
    // Hide all views
    domCache.weekView.style.display = 'none';
    domCache.monthView.style.display = 'none';
    domCache.dayView.style.display = 'none';
    domCache.weekDaysHeader.style.display = 'none';

    // Update view buttons
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-view') === activeView) {
            btn.classList.add('active');
        }
    });

    // Render active view
    if (activeView === 'week') {
        domCache.weekView.style.display = 'grid';
        domCache.weekDaysHeader.style.display = 'grid';
        renderWeekView(currentDate, calendarEvents, tasks);
    } else if (activeView === 'month') {
        domCache.monthView.style.display = 'block';
        renderMonthView(currentMonth, currentYear, currentDate, calendarEvents, tasks);
    } else if (activeView === 'day') {
        domCache.dayView.style.display = 'block';
        renderDayView(currentDate, calendarEvents, tasks);
    }

    renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks);
}

function updateMainCalendarHeader() {
    const monthNames = getMonthNames();
    if (domCache.mainCalendarHeader) {
        domCache.mainCalendarHeader.textContent = `${monthNames[currentMonth - 1]}, ${currentYear}`;
    }
}

function updateMainHeaderForDayView() {
    if (domCache.mainCalendarHeader) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const dateStr = currentDate.toLocaleDateString('en-US', options);
        domCache.mainCalendarHeader.textContent = dateStr;
    }
}

//=============================================================================
// EVENT HANDLERS
// =============================================================================

function initializeEventHandlers() {
    // View switchers
    document.querySelectorAll('.view-btn').forEach(button => {
        button.addEventListener('click', async function () {
            const view = this.getAttribute('data-view');
            activeView = view;

            const [data, _] = await Promise.all([
                fetchCalendarData(currentDate, view),
                fetchUpcomingEvents()
            ]);

            if (!data) return;

            if (view === 'month') {
                domCache.prevWeek.title = 'Previous Month';
                domCache.nextWeek.title = 'Next Month';
            } else if (view === 'day') {
                domCache.prevWeek.title = 'Previous Day';
                domCache.nextWeek.title = 'Next Day';
            } else {
                domCache.prevWeek.title = 'Previous Week';
                domCache.nextWeek.title = 'Next Week';
            }

            renderCurrentView();
            updateMainCalendarHeader();
        });
    });

    // Navigation buttons
    domCache.prevWeek?.addEventListener('click', async function () {
        if (activeView === 'month') {
            await changeMonth(-1, true);
            await fetchUpcomingEvents();
            renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks);
        } else if (activeView === 'day') {
            const newDate = new Date(currentDate);
            newDate.setDate(newDate.getDate() - 1);
            await navigateToDate(newDate, 'day');
        } else {
            const newDate = new Date(currentDate);
            newDate.setDate(newDate.getDate() - DAYS_PER_WEEK);
            await navigateToDate(newDate);
        }
    });

    domCache.nextWeek?.addEventListener('click', async function () {
        if (activeView === 'month') {
            await changeMonth(1, true);
            await fetchUpcomingEvents();
            renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks);
        } else if (activeView === 'day') {
            const newDate = new Date(currentDate);
            newDate.setDate(newDate.getDate() + 1);
            await navigateToDate(newDate, 'day');
        } else {
            const newDate = new Date(currentDate);
            newDate.setDate(newDate.getDate() + DAYS_PER_WEEK);
            await navigateToDate(newDate);
        }
    });

    domCache.todayBtn?.addEventListener('click', async function () {
        await navigateToDate(new Date());
    });

    // Mini calendar month navigation
    domCache.prevMonth?.addEventListener('click', async function () {
        await changeMonth(-1, activeView === 'month');
    });

    domCache.nextMonth?.addEventListener('click', async function () {
        await changeMonth(1, activeView === 'month');
    });

    // Event modal handlers
    domCache.addEventBtn?.addEventListener('click', function () {
        domCache.eventModal.classList.add('active');
        const today = new Date().toISOString().split('T')[0];
        domCache.eventDate.value = today;
    });

    domCache.closeModal?.addEventListener('click', function () {
        domCache.eventModal.classList.remove('active');
        domCache.eventForm.reset();
    });

    domCache.cancelBtn?.addEventListener('click', function () {
        domCache.eventModal.classList.remove('active');
        domCache.eventForm.reset();
    });

    domCache.eventModal?.addEventListener('click', function (e) {
        if (e.target === domCache.eventModal) {
            domCache.eventModal.classList.remove('active');
            domCache.eventForm.reset();
        }
    });

    domCache.eventForm?.addEventListener('submit', function (e) {
        e.preventDefault();

        const formData = new FormData(domCache.eventForm);
        const eventData = {
            title: formData.get('title'),
            description: formData.get('description'),
            location: formData.get('location'),
            start: `${formData.get('date')}T${formData.get('start_time')}:00`,
            end: `${formData.get('date')}T${formData.get('end_time')}:00`
        };

        fetch('/calendar/api/create_event', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(eventData)
        })
            .then(response => response.json())
            .then(async data => {
                if (data.success) {
                    showNotification('Event created successfully!', 'success');
                    domCache.eventModal.classList.remove('active');
                    domCache.eventForm.reset();
                    await refreshCalendarView();
                } else {
                    showNotification('Error creating event: ' + data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Failed to create event', 'error');
            });
    });

    // Task details modal
    domCache.closeTaskDetails?.addEventListener('click', closeTaskDetailsModal);
    domCache.closeTaskDetailsBtn?.addEventListener('click', closeTaskDetailsModal);

    domCache.editTaskBtn?.addEventListener('click', function () {
        if (isGoogleCalendarEvent && currentEventId) {
            const currentEvent = calendarEvents.find(e => e.id === currentEventId);
            if (currentEvent && currentEvent.htmlLink) {
                window.open(currentEvent.htmlLink, '_blank');
            } else {
                const encodedEventId = encodeURIComponent(currentEventId);
                const googleCalendarUrl = `https://calendar.google.com/calendar/u/0/r/eventedit/${encodedEventId}`;
                window.open(googleCalendarUrl, '_blank');
            }
        } else if (currentTaskId) {
            window.location.href = `/tasks/edit/${currentTaskId}`;
        }
    });

    taskDetailsModal?.addEventListener('click', function (e) {
        if (e.target === taskDetailsModal) {
            closeTaskDetailsModal();
        }
    });

    // Sync/remove task handlers
    document.querySelectorAll('.sync-task').forEach(button => {
        button.addEventListener('click', function () {
            const taskId = this.getAttribute('data-task-id');

            fetch(`/calendar/sync_task/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
                .then(response => response.json())
                .then(async data => {
                    if (data.success) {
                        showNotification(data.message, 'success');
                        await refreshCalendarView();
                    } else {
                        showNotification('Error: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('An error occurred while syncing the task.', 'error');
                });
        });
    });

    document.querySelectorAll('.remove-task').forEach(button => {
        button.addEventListener('click', async function () {
            const confirmed = await showStudyConfirmModal(
                'Remove from Google Calendar',
                'Remove this task from your Google Calendar? It will stay in BrainDump but won\'t appear on your calendar.',
                'fas fa-calendar-times',
                'Yes, Remove',
                '#e53935'
            );
            if (!confirmed) return;

            const taskId = this.getAttribute('data-task-id');

            fetch(`/calendar/remove_task/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
                .then(response => response.json())
                .then(async data => {
                    if (data.success) {
                        showNotification(data.message, 'success');
                        await refreshCalendarView();
                    } else {
                        showNotification('Error: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('An error occurred.', 'error');
                });
        });
    });
}

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', async function () {
    // Initialize DOM element cache
    initializeDOMCache();
    
    // Get initial date and view
    let initialDate, initialView, initialCalendarConnected;

    if (domCache.initialDataElement) {
        try {
            const initialData = JSON.parse(domCache.initialDataElement.textContent);
            initialDate = initialData.initialDate;
            initialView = initialData.initialView;
            initialCalendarConnected = initialData.calendarConnected;
        } catch (e) {
            console.error('Failed to parse initial data:', e);
        }
    }

    const urlParams = new URLSearchParams(window.location.search);
    const dateParam = initialDate || urlParams.get('date') || new Date().toISOString().split('T')[0];
    const viewParam = initialView || urlParams.get('view') || 'week';

    currentDate = new Date(dateParam);
    activeView = viewParam;
    currentMonth = currentDate.getMonth() + 1;
    currentYear = currentDate.getFullYear();
    calendarConnected = initialCalendarConnected || false;

    // Fetch initial data
    const [data, _] = await Promise.all([
        fetchCalendarData(currentDate, activeView),
        fetchUpcomingEvents()
    ]);

    if (data) {
        initializeEventHandlers();
        renderCurrentView();
        renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);
        updateMiniCalendarHeader(currentMonth, currentYear);
        renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks);
    } else {
        console.warn('Failed to fetch initial data, initializing with empty state');
        calendarEvents = [];
        tasks = [];
        initializeEventHandlers();
        renderCurrentView();
        renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);
        updateMiniCalendarHeader(currentMonth, currentYear);
        renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks);
    }
});

// Make modals available globally for imported modules
window.showCalendarEventDetails = showCalendarEventDetails;
window.showTaskDetails = showTaskDetails;
