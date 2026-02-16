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
// DATA FETCHING
// =============================================================================

async function fetchCalendarData(date, view) {
    const dateStr = date.toISOString().split('T')[0];

    try {
        const response = await fetch(`/api/calendar/events?date=${dateStr}&view=${view}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            console.error('Failed to fetch calendar data:', data.error);
            alert('Failed to load calendar data: ' + (data.error || 'Unknown error'));
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
        alert('Error loading calendar. Please refresh the page.');
        return false;
    }
}

async function fetchUpcomingEvents() {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];

    try {
        const response = await fetch(`/api/calendar/events?date=${todayStr}&view=week`);

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
    document.getElementById('weekView').style.display = 'none';
    document.getElementById('monthView').style.display = 'none';
    document.getElementById('dayView').style.display = 'none';
    document.querySelector('.week-days-header').style.display = 'none';

    // Update view buttons
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-view') === activeView) {
            btn.classList.add('active');
        }
    });

    // Render active view
    if (activeView === 'week') {
        document.getElementById('weekView').style.display = 'grid';
        document.querySelector('.week-days-header').style.display = 'grid';
        renderWeekView(currentDate, calendarEvents, tasks);
    } else if (activeView === 'month') {
        document.getElementById('monthView').style.display = 'block';
        renderMonthView(currentMonth, currentYear, currentDate, calendarEvents, tasks);
    } else if (activeView === 'day') {
        document.getElementById('dayView').style.display = 'block';
        renderDayView(currentDate, calendarEvents, tasks);
    }

    renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks);
}

function updateMainCalendarHeader() {
    const monthNames = getMonthNames();
    const mainHeader = document.getElementById('mainCalendarHeader');
    if (mainHeader) {
        mainHeader.textContent = `${monthNames[currentMonth - 1]}, ${currentYear}`;
    }
}

function updateMainHeaderForDayView() {
    const mainHeader = document.getElementById('mainCalendarHeader');
    if (mainHeader) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const dateStr = currentDate.toLocaleDateString('en-US', options);
        mainHeader.textContent = dateStr;
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
                document.getElementById('prevWeek').title = 'Previous Month';
                document.getElementById('nextWeek').title = 'Next Month';
            } else if (view === 'day') {
                document.getElementById('prevWeek').title = 'Previous Day';
                document.getElementById('nextWeek').title = 'Next Day';
            } else {
                document.getElementById('prevWeek').title = 'Previous Week';
                document.getElementById('nextWeek').title = 'Next Week';
            }

            renderCurrentView();
            updateMainCalendarHeader();
        });
    });

    // Navigation buttons
    document.getElementById('prevWeek')?.addEventListener('click', async function () {
        if (activeView === 'month') {
            currentMonth--;
            if (currentMonth < 1) {
                currentMonth = 12;
                currentYear--;
            }
            const maxDayInMonth = new Date(currentYear, currentMonth, 0).getDate();
            const newDay = Math.min(currentDate.getDate(), maxDayInMonth);
            currentDate = new Date(currentYear, currentMonth - 1, newDay);

            const [data, _] = await Promise.all([
                fetchCalendarData(currentDate, 'month'),
                fetchUpcomingEvents()
            ]);

            if (data) {
                updateMiniCalendarHeader(currentMonth, currentYear);
                updateMainCalendarHeader();
                renderMonthView(currentMonth, currentYear, currentDate, calendarEvents, tasks);
                renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);
                renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks);
            }
        } else if (activeView === 'day') {
            const newDate = new Date(currentDate);
            newDate.setDate(newDate.getDate() - 1);
            await navigateToDate(newDate, 'day');
        } else {
            const newDate = new Date(currentDate);
            newDate.setDate(newDate.getDate() - 7);
            await navigateToDate(newDate);
        }
    });

    document.getElementById('nextWeek')?.addEventListener('click', async function () {
        if (activeView === 'month') {
            currentMonth++;
            if (currentMonth > 12) {
                currentMonth = 1;
                currentYear++;
            }
            const maxDayInMonth = new Date(currentYear, currentMonth, 0).getDate();
            const newDay = Math.min(currentDate.getDate(), maxDayInMonth);
            currentDate = new Date(currentYear, currentMonth - 1, newDay);

            const [data, _] = await Promise.all([
                fetchCalendarData(currentDate, 'month'),
                fetchUpcomingEvents()
            ]);

            if (data) {
                updateMiniCalendarHeader(currentMonth, currentYear);
                updateMainCalendarHeader();
                renderMonthView(currentMonth, currentYear, currentDate, calendarEvents, tasks);
                renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);
                renderUpcomingEvents(upcomingCalendarEvents, upcomingTasks);
            }
        } else if (activeView === 'day') {
            const newDate = new Date(currentDate);
            newDate.setDate(newDate.getDate() + 1);
            await navigateToDate(newDate, 'day');
        } else {
            const newDate = new Date(currentDate);
            newDate.setDate(newDate.getDate() + 7);
            await navigateToDate(newDate);
        }
    });

    document.getElementById('todayBtn')?.addEventListener('click', async function () {
        await navigateToDate(new Date());
    });

    // Mini calendar month navigation
    document.getElementById('prevMonth')?.addEventListener('click', async function () {
        currentMonth--;
        if (currentMonth < 1) {
            currentMonth = 12;
            currentYear--;
        }

        const maxDayInMonth = new Date(currentYear, currentMonth, 0).getDate();
        const newDay = Math.min(currentDate.getDate(), maxDayInMonth);
        currentDate = new Date(currentYear, currentMonth - 1, newDay);

        updateMiniCalendarHeader(currentMonth, currentYear);
        renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);

        if (activeView === 'month') {
            const data = await fetchCalendarData(currentDate, 'month');
            if (data) {
                renderMonthView(currentMonth, currentYear, currentDate, calendarEvents, tasks);
                updateMainCalendarHeader();
            }
        }
    });

    document.getElementById('nextMonth')?.addEventListener('click', async function () {
        currentMonth++;
        if (currentMonth > 12) {
            currentMonth = 1;
            currentYear++;
        }

        const maxDayInMonth = new Date(currentYear, currentMonth, 0).getDate();
        const newDay = Math.min(currentDate.getDate(), maxDayInMonth);
        currentDate = new Date(currentYear, currentMonth - 1, newDay);

        updateMiniCalendarHeader(currentMonth, currentYear);
        renderMiniCalendar(currentMonth, currentYear, currentDate, calendarEvents, tasks, navigateToDate);

        if (activeView === 'month') {
            const data = await fetchCalendarData(currentDate, 'month');
            if (data) {
                renderMonthView(currentMonth, currentYear, currentDate, calendarEvents, tasks);
                updateMainCalendarHeader();
            }
        }
    });

    // Event modal handlers
    const eventModal = document.getElementById('eventModal');
    const addEventBtn = document.getElementById('addEventBtn');
    const closeModal = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const eventForm = document.getElementById('eventForm');

    addEventBtn?.addEventListener('click', function () {
        eventModal.classList.add('active');
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('eventDate').value = today;
    });

    closeModal?.addEventListener('click', function () {
        eventModal.classList.remove('active');
        eventForm.reset();
    });

    cancelBtn?.addEventListener('click', function () {
        eventModal.classList.remove('active');
        eventForm.reset();
    });

    eventModal?.addEventListener('click', function (e) {
        if (e.target === eventModal) {
            eventModal.classList.remove('active');
            eventForm.reset();
        }
    });

    eventForm?.addEventListener('submit', function (e) {
        e.preventDefault();

        const formData = new FormData(eventForm);
        const eventData = {
            title: formData.get('title'),
            description: formData.get('description'),
            location: formData.get('location'),
            start: `${formData.get('date')}T${formData.get('start_time')}:00`,
            end: `${formData.get('date')}T${formData.get('end_time')}:00`
        };

        fetch('/api/calendar/event', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(eventData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Event created successfully!');
                    eventModal.classList.remove('active');
                    eventForm.reset();
                    location.reload();
                } else {
                    alert('Error creating event: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to create event');
            });
    });

    // Task details modal
    const taskDetailsModal = document.getElementById('taskDetailsModal');
    const closeTaskDetails = document.getElementById('closeTaskDetails');
    const closeTaskDetailsBtn = document.getElementById('closeTaskDetailsBtn');
    const editTaskBtn = document.getElementById('editTaskBtn');

    closeTaskDetails?.addEventListener('click', closeTaskDetailsModal);
    closeTaskDetailsBtn?.addEventListener('click', closeTaskDetailsModal);

    editTaskBtn?.addEventListener('click', function () {
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
            window.location.href = `/edit_task/${currentTaskId}`;
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

            fetch(`/sync_task_to_calendar/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while syncing the task.');
                });
        });
    });

    document.querySelectorAll('.remove-task').forEach(button => {
        button.addEventListener('click', function () {
            if (!confirm('Remove this task from Google Calendar?')) return;

            const taskId = this.getAttribute('data-task-id');

            fetch(`/remove_task_from_calendar/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred.');
                });
        });
    });
}

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', async function () {
    // Get initial date and view
    const initialDataElement = document.getElementById('initialData');
    let initialDate, initialView, initialCalendarConnected;

    if (initialDataElement) {
        try {
            const initialData = JSON.parse(initialDataElement.textContent);
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
