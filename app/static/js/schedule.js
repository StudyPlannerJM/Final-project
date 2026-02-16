// =============================================================================
// INITIALIZE CALENDAR DATA FROM JSON SCRIPT TAG
// =============================================================================
// Global state
let calendarEvents = [];  // Google Calendar events
let tasks = [];           // Local tasks
let upcomingCalendarEvents = [];  // Always fetched from TODAY for upcoming section
let upcomingTasks = [];           // Always fetched from TODAY for upcoming section
let monthEvents = {};     // Event counts by date for mini-calendar
let currentDate;
let currentMonth;
let currentYear;
let activeView = 'week';
let calendarConnected = false;

// Modal-related global variables
let taskDetailsModal;
let closeTaskDetails;
let closeTaskDetailsBtn;
let editTaskBtn;
let currentTaskId = null;
let currentEventId = null;
let isGoogleCalendarEvent = false;

//Function to fetch calendar data via AJAX
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

        // Update global state
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

// Function to fetch upcoming events (always from TODAY, regardless of viewed date)
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
            // Store upcoming events separately
            upcomingCalendarEvents = data.calendarEvents || [];
            upcomingTasks = data.tasks || [];
        }
    } catch (error) {
        console.error('Error fetching upcoming events:', error);
        // Don't show alert for upcoming events failure, just log it
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async function () {
    // Get initial date and view from JSON script tag
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
    
    // Fall back to URL params or defaults
    const urlParams = new URLSearchParams(window.location.search);
    const dateParam = initialDate || urlParams.get('date') || new Date().toISOString().split('T')[0];
    const viewParam = initialView || urlParams.get('view') || 'week';

    currentDate = new Date(dateParam);
    activeView = viewParam;
    currentMonth = currentDate.getMonth() + 1;
    currentYear = currentDate.getFullYear();
    calendarConnected = initialCalendarConnected || false;

    // Fetch initial data and upcoming events in parallel
    const [data, _] = await Promise.all([
        fetchCalendarData(currentDate, activeView),
        fetchUpcomingEvents()
    ]);

    if (data) {
        // Initialize calendar with fetched data
        initializeCalendar();

        // Render appropriate view
        renderCurrentView();
        renderMiniCalendar();
        updateMiniCalendarHeader();
        
        // Explicitly render upcoming events after everything is set up
        renderUpcomingEvents();
    } else {
        // Even if fetch fails, initialize calendar with empty data
        console.warn('Failed to fetch initial data, initializing with empty state');
        calendarEvents = [];
        tasks = [];
        upcomingCalendarEvents = [];
        upcomingTasks = [];
        initializeCalendar();
        renderCurrentView();
        renderMiniCalendar();
        updateMiniCalendarHeader();
        renderUpcomingEvents();
    }
});

// =============================================================================
// HELPER FUNCTIONS (Global Scope)
// =============================================================================

function updateMainCalendarHeader() {
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
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

// =============================================================================
// RENDER UPCOMING EVENTS
// =============================================================================

function renderUpcomingEvents() {
    const upcomingContainer = document.getElementById('upcomingEventsList');
    if (!upcomingContainer) return;

    // Get current date (start of today) and 7 days from now (end of day)
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const weekFromNow = new Date();
    weekFromNow.setDate(weekFromNow.getDate() + 7);
    weekFromNow.setHours(23, 59, 59, 999);

    // Collect all events (calendar + tasks) in the next 7 days
    const upcomingEvents = [];

    // Add Google Calendar events from the UPCOMING events array (always from today)
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

    // Add local tasks from the UPCOMING tasks array (always from today)
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
                No upcoming events in the next 7 days
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

// Helper function to escape HTML and prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// RENDER CURRENT VIEW
// =============================================================================

// NEW: Single function to render whichever view is active
function renderCurrentView() {
    // Hide all views first
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

    // Render the active view
    if (activeView === 'week') {
        document.getElementById('weekView').style.display = 'grid';
        document.querySelector('.week-days-header').style.display = 'grid';
        renderWeekView();
    } else if (activeView === 'month') {
        document.getElementById('monthView').style.display = 'block';
        renderMonthView();
    } else if (activeView === 'day') {
        document.getElementById('dayView').style.display = 'block';
        renderDayView();
    }

    // Always render upcoming events
    renderUpcomingEvents();
}

// =============================================================================
// HELPER FUNCTIONS (GLOBAL SCOPE)
// =============================================================================

function getCategoryColor(category) {
    // Handle new category object format
    if (category && typeof category === 'object' && category.color) {
        return category.color;
    }

    // Fallback for old string format or default
    const colors = {
        'Work': '#4285f4',
        'Personal': '#ea4335',
        'Study': '#fbbc04',
        'Health': '#34a853',
        'Other': '#9e9e9e'
    };
    return colors[category] || colors['Other'];
}

function formatTime(date) {
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    return `${displayHours}:${String(minutes).padStart(2, '0')} ${ampm}`;
}

function showCalendarEventDetails(event) {
    isGoogleCalendarEvent = true;
    currentEventId = event.id;
    currentTaskId = null;

    // Update modal title
    document.getElementById('taskDetailsTitle').textContent = 'Google Calendar Event';

    // Populate modal with event details
    document.getElementById('detailTitle').textContent = event.title || 'No title';

    const descEl = document.getElementById('detailDescription');
    if (event.description) {
        descEl.textContent = event.description;
        descEl.classList.remove('empty');
    } else {
        descEl.textContent = 'No description provided';
        descEl.classList.add('empty');
    }

    // Format dates
    const startDate = new Date(event.start);
    const endDate = new Date(event.end);
    document.getElementById('detailDueDate').textContent = startDate.toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }) + ' - ' + endDate.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });

    // Hide category and status for calendar events
    document.getElementById('detailCategory').parentElement.style.display = 'none';
    document.getElementById('detailStatus').parentElement.style.display = 'none';

    // Show location if available
    if (event.location) {
        const categoryEl = document.getElementById('detailCategory').parentElement;
        categoryEl.style.display = 'flex';
        categoryEl.querySelector('.detail-label').innerHTML = '<i class="fas fa-map-marker-alt"></i> Location:';
        document.getElementById('detailCategory').textContent = event.location;
    }

    // Hide synced status
    document.getElementById('detailSyncedRow').style.display = 'none';

    // Update button text
    editTaskBtn.textContent = 'Edit in Google Calendar';

    // Show modal
    taskDetailsModal.classList.add('active');
}

function showTaskDetails(task) {
    isGoogleCalendarEvent = false;
    currentTaskId = task.id;
    currentEventId = null;

    // Reset modal title
    document.getElementById('taskDetailsTitle').textContent = 'Task Details';

    // Populate modal with task details
    document.getElementById('detailTitle').textContent = task.title || 'No title';

    const descEl = document.getElementById('detailDescription');
    if (task.description) {
        descEl.textContent = task.description;
        descEl.classList.remove('empty');
    } else {
        descEl.textContent = 'No description provided';
        descEl.classList.add('empty');
    }

    // Format due date
    if (task.due_date) {
        const dueDate = new Date(task.due_date.replace(' ', 'T'));
        document.getElementById('detailDueDate').textContent = dueDate.toLocaleString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } else {
        document.getElementById('detailDueDate').textContent = 'No due date';
    }

    document.getElementById('detailCategory').parentElement.style.display = 'flex';
    document.getElementById('detailCategory').parentElement.querySelector('.detail-label').innerHTML = '<i class="fas fa-folder"></i> Category:';

    // Display category with color and icon if available
    const categoryEl = document.getElementById('detailCategory');
    if (task.category && task.category.name) {
        const categoryHTML = `<span style="background-color: ${task.category.color}; color: white; padding: 4px 8px; border-radius: 4px; display: inline-block;">
            ${task.category.icon ? task.category.icon + ' ' : ''}${task.category.name}
        </span>`;
        categoryEl.innerHTML = categoryHTML;
    } else {
        // Show a muted badge for uncategorized tasks
        categoryEl.innerHTML = '<span style="background-color: #95a5a6; color: white; padding: 4px 8px; border-radius: 4px; display: inline-block; font-style: italic;">Uncategorized</span>';
    }

    document.getElementById('detailStatus').parentElement.style.display = 'flex';
    document.getElementById('detailStatus').textContent = task.status || 'pending';

    // Update button text
    editTaskBtn.textContent = 'Edit Task';

    // Show synced status if applicable
    if (task.synced) {
        document.getElementById('detailSyncedRow').style.display = 'flex';
        document.getElementById('detailSynced').textContent = 'Yes - Synced to Google Calendar';
    } else {
        document.getElementById('detailSyncedRow').style.display = 'none';
    }

    // Show modal
    taskDetailsModal.classList.add('active');
}

function renderMiniCalendar() {
    const calendarDays = document.getElementById('calendarDays');
    if (!calendarDays) return;

    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    const lastDay = new Date(currentYear, currentMonth, 0);
    const prevLastDay = new Date(currentYear, currentMonth - 1, 0);

    const firstDayIndex = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
    const lastDayDate = lastDay.getDate();
    const prevLastDayDate = prevLastDay.getDate();

    const today = new Date();
    
    // Calculate event counts for this month from current data
    monthEvents = {};
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
    const viewingSelectedMonth = currentDate.getMonth() + 1 === currentMonth && currentDate.getFullYear() === currentYear;

    let daysHTML = '';

    // Previous month days
    for (let i = firstDayIndex; i > 0; i--) {
        daysHTML += `<div class="calendar-day other-month">${prevLastDayDate - i + 1}</div>`;
    }

    // Current month days
    for (let day = 1; day <= lastDayDate; day++) {
        const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const isSelected = viewingSelectedMonth && currentDate.getDate() === day;
        const hasEvents = monthEvents[dateStr] && monthEvents[dateStr] > 0;

        const classes = ['calendar-day'];

        // Only highlight the selected date
        if (isSelected) {
            classes.push('selected');
        }

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
        dayEl.addEventListener('click', async function () {
            const selectedDate = this.getAttribute('data-date');
            if (selectedDate) {
                const newDate = new Date(selectedDate);
                await navigateToDate(newDate, activeView);
            }
        });
    });
}

function updateMiniCalendarHeader() {
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    document.getElementById('currentMonthYear').textContent = `${monthNames[currentMonth - 1]} ${currentYear}`;
}

async function navigateToDate(date, view = null) {
    const viewParam = view || activeView;

    // Update current date
    currentDate = new Date(date);
    currentMonth = currentDate.getMonth() + 1;
    currentYear = currentDate.getFullYear();

    // Fetch new data via AJAX (NO PAGE RELOAD!)
    // Also fetch upcoming events to keep them fresh
    const [data, _] = await Promise.all([
        fetchCalendarData(currentDate, viewParam),
        fetchUpcomingEvents()
    ]);

    if (data) {
        // Update URL without reloading page
        const dateStr = currentDate.toISOString().split('T')[0];
        const newUrl = `/schedule?date=${dateStr}&view=${viewParam}`;
        window.history.pushState({ date: dateStr, view: viewParam }, '', newUrl);

        // Re-render the calendar with new data
        renderCurrentView();
        renderMiniCalendar();
        updateMiniCalendarHeader();
        updateMainCalendarHeader();
    } else {
        console.error('Failed to navigate to date:', date);
    }
}

function renderWeekView() {
    // ====================================================================
    // STEP 1: Build the week grid structure (headers, time column, day columns)
    // ====================================================================
    
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
            <span class="day-name">${day.toLocaleDateString('en-US', {weekday: 'long'})}</span>
            <span class="day-number">${day.getDate()}</span>
            <span class="day-date">${day.toLocaleDateString('en-US', {month: 'short', day: 'numeric'})}</span>
        `;
        weekHeader.appendChild(dayHeader);
    }
    
    // Build time column (00:00 to 23:00)
    const timeColumn = document.getElementById('weekTimeColumn');
    timeColumn.innerHTML = ''; // Clear existing
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
            hourSlot.addEventListener('click', function() {
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
    
    // ====================================================================
    // STEP 2: Now render events on the grid that we just built
    // ====================================================================
    
    // Clear existing events
    document.querySelectorAll('.event-block').forEach(el => el.remove());

    // Render Google Calendar events
    calendarEvents.forEach(event => {
        // Parse dates properly to avoid timezone issues
        const startDate = new Date(event.start);
        const endDate = new Date(event.end);

        const dateStr = event.start.split('T')[0];
        const dayColumn = document.querySelector(`.day-column[data-date="${dateStr}"]`);

        if (!dayColumn) return;

        const startHour = startDate.getHours();
        const startMinutes = startDate.getMinutes();

        // Find the correct hour slot
        const hourSlot = dayColumn.querySelector(`.hour-slot[data-hour="${startHour}"]`);
        if (!hourSlot) {
            console.warn(`No hour slot found for hour: ${startHour} in date: ${dateStr}`);
            return;
        }

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
    tasks.forEach((task, index) => {
        if (!task.due_date) return;

        // Parse date string components to avoid timezone issues
        const [datePart, timePart] = task.due_date.split('T');
        const [year, month, day] = datePart.split('-').map(Number);
        const [hour, minute] = timePart.split(':').map(Number);

        const taskDate = new Date(year, month - 1, day, hour, minute);
        const dateStr = datePart;

        const dayColumn = document.querySelector(`.day-column[data-date="${dateStr}"]`);
        if (!dayColumn) {
            console.warn(`No day column found for date: ${dateStr}`);
            return;
        }

        // Find the correct hour slot
        const hourSlot = dayColumn.querySelector(`.hour-slot[data-hour="${hour}"]`);
        if (!hourSlot) {
            console.warn(`No hour slot found for hour: ${hour} in date: ${dateStr}`);
            return;
        }

        const taskBlock = document.createElement('div');
        taskBlock.className = 'event-block task-block';
        taskBlock.classList.add(`status-${task.status}`);
        if (task.synced) taskBlock.classList.add('synced');

        // Set border color based on category
        const categoryColor = getCategoryColor(task.category);
        taskBlock.style.borderLeftColor = categoryColor;
        taskBlock.style.backgroundColor = categoryColor + '25'; // Add transparency

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

    // Adjust hour slot heights based on number of tasks
    const grid = document.querySelector('.week-calendar-grid');
    const gridTimeColumn = grid.querySelector('.time-column');
    const timeSlots = Array.from(gridTimeColumn.querySelectorAll('.time-slot'));

    // Track max tasks per hour across all days
    const maxTasksPerHour = new Array(24).fill(0);

    document.querySelectorAll('.day-column').forEach(dayColumn => {
        dayColumn.querySelectorAll('.hour-slot').forEach(hourSlot => {
            const hour = parseInt(hourSlot.getAttribute('data-hour'));
            const tasksInSlot = hourSlot.querySelectorAll('.event-block').length;
            maxTasksPerHour[hour] = Math.max(maxTasksPerHour[hour], tasksInSlot);
        });
    });

    // Apply heights to all columns uniformly
    maxTasksPerHour.forEach((taskCount, hour) => {
        const newHeight = taskCount > 1 ? (taskCount * 60) : 60;

        // Update time slot
        if (timeSlots[hour]) {
            timeSlots[hour].style.height = `${newHeight}px`;
            timeSlots[hour].style.minHeight = `${newHeight}px`;
        }

        // Update all day column hour slots for this hour
        document.querySelectorAll(`.hour-slot[data-hour="${hour}"]`).forEach(slot => {
            slot.style.height = `${newHeight}px`;
            slot.style.minHeight = `${newHeight}px`;
        });
    });
}

function renderDayView() {
    const dayEventsColumn = document.getElementById('dayEventsColumn');
    if (!dayEventsColumn) {
        console.error('dayEventsColumn not found!');
        return;
    }

    // Use currentDate to get the date string, not stale HTML attribute
    const dateStr = currentDate.toISOString().split('T')[0];
    
    // Update the data-date attribute to match current date
    dayEventsColumn.setAttribute('data-date', dateStr);

    // Update the large day header with formatted date and TODAY badge
    const dayHeader = document.getElementById('dayViewDateHeader');
    if (dayHeader) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const formattedDate = currentDate.toLocaleDateString('en-US', options);

        // Check if viewing today
        const today = new Date();
        const isToday = currentDate.toDateString() === today.toDateString();

        if (isToday) {
            dayHeader.innerHTML = `${formattedDate} <span class="today-badge">TODAY</span>`;
        } else {
            dayHeader.textContent = formattedDate;
        }
    }

    updateMainHeaderForDayView();

    // Clear existing events
    dayEventsColumn.querySelectorAll('.event-block').forEach(el => el.remove());

    // Reset all hour slot heights
    const timeSlots = document.querySelector('.day-grid .time-column').querySelectorAll('.time-slot');
    dayEventsColumn.querySelectorAll('.hour-slot').forEach(slot => {
        slot.style.height = '60px';
        slot.style.minHeight = '60px';
    });

    // Track events per hour for height adjustment
    const eventsPerHour = new Array(24).fill(0);

    // Render Google Calendar events
    calendarEvents.forEach(event => {
        const eventDate = event.start.split('T')[0];
        if (eventDate !== dateStr) return;

        const startDate = new Date(event.start);
        const endDate = new Date(event.end);
        const startHour = startDate.getHours();

        const hourSlot = dayEventsColumn.querySelector(`.hour-slot[data-hour="${startHour}"]`);
        if (!hourSlot) return;

        eventsPerHour[startHour]++;

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

        const taskDate = task.due_date.split('T')[0];
        if (taskDate !== dateStr) return;

        const [datePart, timePart] = task.due_date.split('T');
        const [year, month, day] = datePart.split('-').map(Number);
        const [hour, minute] = timePart.split(':').map(Number);

        const hourSlot = dayEventsColumn.querySelector(`.hour-slot[data-hour="${hour}"]`);
        if (!hourSlot) return;

        eventsPerHour[hour]++;

        const taskBlock = document.createElement('div');
        taskBlock.className = 'event-block task-block';
        taskBlock.classList.add(`status-${task.status}`);
        if (task.synced) taskBlock.classList.add('synced');

        const categoryColor = getCategoryColor(task.category);
        taskBlock.style.borderLeftColor = categoryColor;
        taskBlock.style.backgroundColor = categoryColor + '25';

        const taskDateObj = new Date(year, month - 1, day, hour, minute);
        taskBlock.innerHTML = `
            <div class="event-time-range">${formatTime(taskDateObj)}</div>
            <div class="event-title">${task.title}</div>
        `;

        taskBlock.style.cursor = 'pointer';
        taskBlock.addEventListener('click', function (e) {
            e.stopPropagation();
            showTaskDetails(task);
        });

        hourSlot.appendChild(taskBlock);
    });

    // Adjust hour slot heights based on event count
    eventsPerHour.forEach((count, hour) => {
        if (count > 1) {
            const newHeight = count * 60;

            if (timeSlots[hour]) {
                timeSlots[hour].style.height = `${newHeight}px`;
                timeSlots[hour].style.minHeight = `${newHeight}px`;
            }

            const hourSlot = dayEventsColumn.querySelector(`.hour-slot[data-hour="${hour}"]`);
            if (hourSlot) {
                hourSlot.style.height = `${newHeight}px`;
                hourSlot.style.minHeight = `${newHeight}px`;
            }
        }
    });
}

function renderMonthView() {
    const monthDaysGrid = document.getElementById('monthDaysGrid');
    monthDaysGrid.innerHTML = '';

    // Get first day of the month
    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    const lastDay = new Date(currentYear, currentMonth, 0);

    // Get the day of week (0 = Sunday, 1 = Monday, etc.)
    // Adjust so Monday is first day (0 = Monday, 6 = Sunday)
    let firstDayOfWeek = firstDay.getDay();
    firstDayOfWeek = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1;

    const daysInMonth = lastDay.getDate();
    const prevMonth = currentMonth === 1 ? 12 : currentMonth - 1;
    const prevMonthYear = currentMonth === 1 ? currentYear - 1 : currentYear;
    const daysInPrevMonth = new Date(prevMonthYear, prevMonth, 0).getDate();

    // Calculate total cells needed
    const totalCells = Math.ceil((firstDayOfWeek + daysInMonth) / 7) * 7;

    // Get today's date
    const today = new Date();
    const isCurrentMonth = today.getMonth() === currentMonth - 1 && today.getFullYear() === currentYear;
    const todayDate = today.getDate();

    // Create array of all events by date
    const eventsByDate = {};

    // Add calendar events (Google Calendar events for the FULL MONTH)
    calendarEvents.forEach(event => {
        const eventDate = event.start.split('T')[0];
        if (!eventsByDate[eventDate]) {
            eventsByDate[eventDate] = [];
        }
        eventsByDate[eventDate].push({
            ...event,
            type: 'calendar'
        });
    });

    // Add tasks
    tasks.forEach(task => {
        if (task.due_date) {
            const taskDate = task.due_date.split('T')[0];
            if (!eventsByDate[taskDate]) {
                eventsByDate[taskDate] = [];
            }
            eventsByDate[taskDate].push({
                ...task,
                title: task.title,
                type: 'task'
            });
        }
    });

    // Render calendar cells
    for (let i = 0; i < totalCells; i++) {
        const cell = document.createElement('div');
        cell.className = 'month-day-cell';

        let day, month, year, isOtherMonth = false;

        // Previous month days
        if (i < firstDayOfWeek) {
            day = daysInPrevMonth - firstDayOfWeek + i + 1;
            month = prevMonth;
            year = prevMonthYear;
            isOtherMonth = true;
        }
        // Current month days
        else if (i < firstDayOfWeek + daysInMonth) {
            day = i - firstDayOfWeek + 1;
            month = currentMonth;
            year = currentYear;
        }
        // Next month days
        else {
            day = i - firstDayOfWeek - daysInMonth + 1;
            month = currentMonth === 12 ? 1 : currentMonth + 1;
            year = currentMonth === 12 ? currentYear + 1 : currentYear;
            isOtherMonth = true;
        }

        if (isOtherMonth) {
            cell.classList.add('other-month');
        }

        if (isCurrentMonth && day === todayDate && !isOtherMonth) {
            cell.classList.add('today');
        }

        // Create date string
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        cell.dataset.date = dateStr;

        // Add day number
        const dayNumber = document.createElement('div');
        dayNumber.className = 'month-day-number';
        dayNumber.textContent = day;
        cell.appendChild(dayNumber);

        // Add events for this day
        const eventsContainer = document.createElement('div');
        eventsContainer.className = 'month-events';

        if (eventsByDate[dateStr]) {
            const dayEvents = eventsByDate[dateStr];
            const maxDisplay = 3;

            dayEvents.slice(0, maxDisplay).forEach(event => {
                const eventItem = document.createElement('div');
                eventItem.className = `month-event-item ${event.type}-event`;
                eventItem.textContent = event.title;

                // Add click handler
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

            // Show "more" indicator if there are more events
            if (dayEvents.length > maxDisplay) {
                const moreItem = document.createElement('div');
                moreItem.className = 'month-event-more';
                moreItem.textContent = `+${dayEvents.length - maxDisplay} more`;
                moreItem.addEventListener('click', function (e) {
                    e.stopPropagation();
                    // Could show a modal with all events for this day
                    alert(`${dayEvents.length} events on this day. Click individual events to view details.`);
                });
                eventsContainer.appendChild(moreItem);
            }
        }

        cell.appendChild(eventsContainer);

        // Add click handler for empty space
        cell.addEventListener('click', function () {
            // Could navigate to day view or show add event dialog
        });

        monthDaysGrid.appendChild(cell);
    }
}

function initializeCalendar() {
    // =============================================================================
    // SYNC/REMOVE TASK HANDLERS
    // =============================================================================

    // Handle sync to calendar
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

    // Handle remove from calendar
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

    // =============================================================================
    // MINI CALENDAR FUNCTIONALITY
    // =============================================================================

    // Month navigation
    document.getElementById('prevMonth')?.addEventListener('click', async function () {
        currentMonth--;
        if (currentMonth < 1) {
            currentMonth = 12;
            currentYear--;
        }
        
        // Update currentDate to match the new month (but keep the day if possible)
        const maxDayInMonth = new Date(currentYear, currentMonth, 0).getDate();
        const newDay = Math.min(currentDate.getDate(), maxDayInMonth);
        currentDate = new Date(currentYear, currentMonth - 1, newDay);
        
        updateMiniCalendarHeader();
        renderMiniCalendar();
        
        // ONLY fetch new data if we're in month view
        if (activeView === 'month') {
            const data = await fetchCalendarData(currentDate, 'month');
            if (data) {
                renderMonthView();
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
        
        // Update currentDate to match the new month (but keep the day if possible)
        const maxDayInMonth = new Date(currentYear, currentMonth, 0).getDate();
        const newDay = Math.min(currentDate.getDate(), maxDayInMonth);
        currentDate = new Date(currentYear, currentMonth - 1, newDay);
        
        updateMiniCalendarHeader();
        renderMiniCalendar();
        
        // ONLY fetch new data if we're in month view
        if (activeView === 'month') {
            const data = await fetchCalendarData(currentDate, 'month');
            if (data) {
                renderMonthView();
                updateMainCalendarHeader();
            }
        }
    });

    //=============================================================================
    // WEEK NAVIGATION
    // =============================================================================

    document.getElementById('prevWeek')?.addEventListener('click', async function () {
        if (activeView === 'month') {
            // Navigate to previous month
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
                updateMiniCalendarHeader();
                updateMainCalendarHeader();
                renderMonthView();
                renderMiniCalendar();
                renderUpcomingEvents();
            }
        } else if (activeView === 'day') {
            // Navigate to previous day
            currentDate.setDate(currentDate.getDate() - 1);
            await navigateToDate(currentDate, 'day');
        } else {
            // Navigate to previous week
            currentDate.setDate(currentDate.getDate() - 7);
            await navigateToDate(currentDate);
        }
    });

    document.getElementById('nextWeek')?.addEventListener('click', async function () {
        if (activeView === 'month') {
            // Navigate to next month
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
                updateMiniCalendarHeader();
                updateMainCalendarHeader();
                renderMonthView();
                renderMiniCalendar();
                renderUpcomingEvents();
            }
        } else if (activeView === 'day') {
            // Navigate to next day
            currentDate.setDate(currentDate.getDate() + 1);
            await navigateToDate(currentDate, 'day');
        } else {
            // Navigate to next week
            currentDate.setDate(currentDate.getDate() + 7);
            await navigateToDate(currentDate);
        }
    });

    document.getElementById('todayBtn')?.addEventListener('click', async function () {
        await navigateToDate(new Date());
    });

    // =============================================================================
    // VIEW SWITCHER (Month/Week/Day)
    // =============================================================================

    document.querySelectorAll('.view-btn').forEach(button => {
        button.addEventListener('click', async function () {
            const view = this.getAttribute('data-view');
            activeView = view;

            // Fetch data for the new view and upcoming events
            const [data, _] = await Promise.all([
                fetchCalendarData(currentDate, view),
                fetchUpcomingEvents()
            ]);

            if (!data) return;

            // Update button text for navigation
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

            // Render the view
            renderCurrentView();
            updateMainCalendarHeader();
        });
    });

    // =============================================================================
    // EVENT MODAL FUNCTIONALITY
    // =============================================================================

    const eventModal = document.getElementById('eventModal');
    const addEventBtn = document.getElementById('addEventBtn');
    const closeModal = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const eventForm = document.getElementById('eventForm');

    // Open modal
    addEventBtn?.addEventListener('click', function () {
        eventModal.classList.add('active');
        // Set default date to today
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('eventDate').value = today;
    });

    // Close modal
    closeModal?.addEventListener('click', function () {
        eventModal.classList.remove('active');
        eventForm.reset();
    });

    cancelBtn?.addEventListener('click', function () {
        eventModal.classList.remove('active');
        eventForm.reset();
    });

    // Close on overlay click
    eventModal?.addEventListener('click', function (e) {
        if (e.target === eventModal) {
            eventModal.classList.remove('active');
            eventForm.reset();
        }
    });

    // Submit event form
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

        // Send to server
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
                    // Show success message
                    alert('Event created successfully!');
                    eventModal.classList.remove('active');
                    eventForm.reset();
                    // Reload page to show new event
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

    // =============================================================================
    // TASK DETAILS MODAL
    // =============================================================================

    // Initialize modal DOM references (variables declared at global scope)
    taskDetailsModal = document.getElementById('taskDetailsModal');
    closeTaskDetails = document.getElementById('closeTaskDetails');
    closeTaskDetailsBtn = document.getElementById('closeTaskDetailsBtn');
    editTaskBtn = document.getElementById('editTaskBtn');

    function closeTaskDetailsModal() {
        taskDetailsModal.classList.remove('active');
        currentTaskId = null;
        currentEventId = null;
        isGoogleCalendarEvent = false;
    }

    closeTaskDetails.addEventListener('click', closeTaskDetailsModal);
    closeTaskDetailsBtn.addEventListener('click', closeTaskDetailsModal);

    editTaskBtn.addEventListener('click', function () {
        if (isGoogleCalendarEvent && currentEventId) {
            // Try to use the htmlLink from the event, otherwise construct URL
            const currentEvent = calendarEvents.find(e => e.id === currentEventId);
            if (currentEvent && currentEvent.htmlLink) {
                window.open(currentEvent.htmlLink, '_blank');
            } else {
                // Fallback: construct URL with encoded event ID
                const encodedEventId = encodeURIComponent(currentEventId);
                const googleCalendarUrl = `https://calendar.google.com/calendar/u/0/r/eventedit/${encodedEventId}`;
                window.open(googleCalendarUrl, '_blank');
            }
        } else if (currentTaskId) {
            window.location.href = `/edit_task/${currentTaskId}`;
        }
    });

    // Close modal when clicking outside
    taskDetailsModal.addEventListener('click', function (e) {
        if (e.target === taskDetailsModal) {
            closeTaskDetailsModal();
        }
    });

    // =============================================================================
    // INITIALIZATION COMPLETE
    // =============================================================================
    // Note: View rendering is handled by DOMContentLoaded after data fetch
    // to avoid duplicate initialization
} // End of initializeCalendar