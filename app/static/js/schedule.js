// =============================================================================
// INITIALIZE CALENDAR DATA FROM JSON SCRIPT TAG
// =============================================================================
let weekEvents = [];
let monthEvents = {};
let tasks = [];
let currentDate;
let currentMonth;
let currentYear;

document.addEventListener('DOMContentLoaded', function() {
    const calendarDataEl = document.getElementById('calendarData');
    const calendarData = calendarDataEl ? JSON.parse(calendarDataEl.textContent) : {};
    
    weekEvents = calendarData.weekEvents || [];
    monthEvents = calendarData.monthEvents || {};
    tasks = calendarData.tasks || [];
    const targetDate = calendarData.targetDate || new Date().toISOString().split('T')[0];
    currentMonth = calendarData.currentMonth || new Date().getMonth() + 1;
    currentYear = calendarData.currentYear || new Date().getFullYear();
    currentDate = new Date(targetDate);
    
    console.log('Calendar data loaded:', { weekEvents, monthEvents, tasks, targetDate, currentMonth, currentYear });
    
    // Initialize calendar after data is loaded
    initializeCalendar();
});

function initializeCalendar() {
    // =============================================================================
    // SYNC/REMOVE TASK HANDLERS
    // =============================================================================

    // Handle sync to calendar
    document.querySelectorAll('.sync-task').forEach(button => {
        button.addEventListener('click', function() {
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
        button.addEventListener('click', function() {
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
            dayEl.addEventListener('click', function() {
                const selectedDate = this.getAttribute('data-date');
                window.location.href = `/schedule?date=${selectedDate}`;
            });
        });
    }

    // Month navigation
    document.getElementById('prevMonth')?.addEventListener('click', function() {
        currentMonth--;
        if (currentMonth < 1) {
            currentMonth = 12;
            currentYear--;
        }
        updateMiniCalendarHeader();
        renderMiniCalendar();
    });

    document.getElementById('nextMonth')?.addEventListener('click', function() {
        currentMonth++;
        if (currentMonth > 12) {
            currentMonth = 1;
            currentYear++;
        }
        updateMiniCalendarHeader();
        renderMiniCalendar();
    });

    function updateMiniCalendarHeader() {
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        document.getElementById('currentMonthYear').textContent = `${monthNames[currentMonth - 1]} ${currentYear}`;
    }

    // =============================================================================
    // WEEK NAVIGATION
    // =============================================================================

    document.getElementById('prevWeek')?.addEventListener('click', function() {
        currentDate.setDate(currentDate.getDate() - 7);
        navigateToDate(currentDate);
    });

    document.getElementById('nextWeek')?.addEventListener('click', function() {
        currentDate.setDate(currentDate.getDate() + 7);
        navigateToDate(currentDate);
    });

    document.getElementById('todayBtn')?.addEventListener('click', function() {
        navigateToDate(new Date());
    });

    function navigateToDate(date) {
        const dateStr = date.toISOString().split('T')[0];
        window.location.href = `/schedule?date=${dateStr}`;
    }

    // =============================================================================
    // VIEW SWITCHER (Month/Week/Day)
    // =============================================================================

    document.querySelectorAll('.view-btn').forEach(button => {
        button.addEventListener('click', function() {
            const view = this.getAttribute('data-view');
            
            // Remove active class from all buttons
            document.querySelectorAll('.view-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Handle different views
            if (view === 'week') {
                // Week view is already displayed (default)
                console.log('Week view active');
            } else if (view === 'month') {
                // Month view not yet implemented
                alert('Month view coming soon! For now, use the mini calendar on the left to navigate.');
            } else if (view === 'day') {
                // Day view not yet implemented
                alert('Day view coming soon! Week view shows daily time slots.');
            }
        });
    });

    // =============================================================================
    // RENDER WEEK EVENTS ON CALENDAR GRID
    // =============================================================================

    function renderWeekEvents() {
        // Clear existing events
        document.querySelectorAll('.event-block').forEach(el => el.remove());

        // Render Google Calendar events
        weekEvents.forEach(event => {
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
            eventBlock.addEventListener('click', function(e) {
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
            
            console.log(`Task: ${task.title}, Hour: ${hour}, Minute: ${minute}, Date: ${dateStr}`);
            
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
            taskBlock.addEventListener('click', function(e) {
                e.stopPropagation();
                showTaskDetails(task);
            });

            hourSlot.appendChild(taskBlock);
            console.log(`Task appended to hour slot ${hour}`);
        });
        
        // Adjust hour slot heights based on number of tasks
        const grid = document.querySelector('.week-calendar-grid');
        const timeColumn = grid.querySelector('.time-column');
        const timeSlots = Array.from(timeColumn.querySelectorAll('.time-slot'));
        
        // Track max tasks per hour across all days
        const maxTasksPerHour = new Array(24).fill(0);
        
        document.querySelectorAll('.day-column').forEach(dayColumn => {
            dayColumn.querySelectorAll('.hour-slot').forEach(hourSlot => {
                const hour = parseInt(hourSlot.getAttribute('data-hour'));
                const tasksInSlot = hourSlot.querySelectorAll('.event-block').length;
                if (tasksInSlot > 0) {
                    console.log(`Hour ${hour}: ${tasksInSlot} tasks`);
                }
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
                if (taskCount > 1) {
                    console.log(`Setting hour ${hour} height to ${newHeight}px for ${taskCount} tasks`);
                }
            }
            
            // Update all day column hour slots for this hour
            document.querySelectorAll(`.hour-slot[data-hour="${hour}"]`).forEach(slot => {
                slot.style.height = `${newHeight}px`;
                slot.style.minHeight = `${newHeight}px`;
            });
        });
    }

    function getCategoryColor(category) {
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

    // =============================================================================
    // EVENT MODAL FUNCTIONALITY
    // =============================================================================

    const eventModal = document.getElementById('eventModal');
    const addEventBtn = document.getElementById('addEventBtn');
    const closeModal = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const eventForm = document.getElementById('eventForm');

    // Open modal
    addEventBtn?.addEventListener('click', function() {
        eventModal.classList.add('active');
        // Set default date to today
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('eventDate').value = today;
    });

    // Close modal
    closeModal?.addEventListener('click', function() {
        eventModal.classList.remove('active');
        eventForm.reset();
    });

    cancelBtn?.addEventListener('click', function() {
        eventModal.classList.remove('active');
        eventForm.reset();
    });

    // Close on overlay click
    eventModal?.addEventListener('click', function(e) {
        if (e.target === eventModal) {
            eventModal.classList.remove('active');
            eventForm.reset();
        }
    });

    // Submit event form
    eventForm?.addEventListener('submit', function(e) {
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
    // HOUR SLOT CLICK TO ADD EVENT
    // =============================================================================

    document.querySelectorAll('.hour-slot').forEach(slot => {
        slot.addEventListener('click', function() {
            const dayColumn = this.closest('.day-column');
            const date = dayColumn.getAttribute('data-date');
            const hour = this.getAttribute('data-hour');

            // Open modal with pre-filled date and time
            eventModal.classList.add('active');
            document.getElementById('eventDate').value = date;
            document.getElementById('eventStartTime').value = `${String(hour).padStart(2, '0')}:00`;
            document.getElementById('eventEndTime').value = `${String(parseInt(hour) + 1).padStart(2, '0')}:00`;
        });
    });

    // =============================================================================
    // TASK DETAILS MODAL
    // =============================================================================

    const taskDetailsModal = document.getElementById('taskDetailsModal');
    const closeTaskDetails = document.getElementById('closeTaskDetails');
    const closeTaskDetailsBtn = document.getElementById('closeTaskDetailsBtn');
    const editTaskBtn = document.getElementById('editTaskBtn');
    let currentTaskId = null;
    let currentEventId = null;
    let isGoogleCalendarEvent = false;

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
        document.getElementById('detailCategory').textContent = task.category || 'None';
        
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

    function closeTaskDetailsModal() {
        taskDetailsModal.classList.remove('active');
        currentTaskId = null;
        currentEventId = null;
        isGoogleCalendarEvent = false;
    }

    closeTaskDetails.addEventListener('click', closeTaskDetailsModal);
    closeTaskDetailsBtn.addEventListener('click', closeTaskDetailsModal);
    
    editTaskBtn.addEventListener('click', function() {
        if (isGoogleCalendarEvent && currentEventId) {
            // Try to use the htmlLink from the event, otherwise construct URL
            const currentEvent = weekEvents.find(e => e.id === currentEventId);
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
    taskDetailsModal.addEventListener('click', function(e) {
        if (e.target === taskDetailsModal) {
            closeTaskDetailsModal();
        }
    });

    // =============================================================================
    // INITIALIZE
    // =============================================================================

    renderMiniCalendar();
    renderWeekEvents();
}