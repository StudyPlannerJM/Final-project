// =============================================================================
// INITIALIZE CALENDAR DATA FROM JSON SCRIPT TAG
// =============================================================================
document.addEventListener('DOMContentLoaded', function() {
    const calendarDataEl = document.getElementById('calendarData');
    const calendarData = calendarDataEl ? JSON.parse(calendarDataEl.textContent) : {};
    
    const weekEvents = calendarData.weekEvents || [];
    const monthEvents = calendarData.monthEvents || {};
    const targetDate = calendarData.targetDate || new Date().toISOString().split('T')[0];
    let currentMonth = calendarData.currentMonth || new Date().getMonth() + 1;
    let currentYear = calendarData.currentYear || new Date().getFullYear();
    let currentDate = new Date(targetDate);
    
    console.log('Calendar data loaded:', { weekEvents, monthEvents, targetDate, currentMonth, currentYear });
});

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
// CALENDAR JavaScript - Handles interactive features
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Get calendar data from template
    const weekEvents = window.calendarData.weekEvents || [];
    const monthEvents = window.calendarData.monthEvents || {};
    let currentDate = new Date(window.calendarData.targetDate);
    let currentMonth = window.calendarData.currentMonth;
    let currentYear = window.calendarData.currentYear;

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

        let daysHTML = '';

        // Previous month days
        for (let i = firstDayIndex; i > 0; i--) {
            daysHTML += `<div class="calendar-day other-month">${prevLastDayDate - i + 1}</div>`;
        }

        // Current month days
        for (let day = 1; day <= lastDayDate; day++) {
            const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = today.getDate() === day && today.getMonth() + 1 === currentMonth && today.getFullYear() === currentYear;
            const hasEvents = monthEvents[dateStr] && monthEvents[dateStr] > 0;

            const classes = ['calendar-day'];
            if (isToday) classes.push('today');
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
        document.querySelectorAll('.calendar-day:not(.other-month)').forEach(dayEl => {
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
    // RENDER WEEK EVENTS ON CALENDAR GRID
    // =============================================================================

    function renderWeekEvents() {
        // Clear existing events
        document.querySelectorAll('.event-block').forEach(el => el.remove());

        weekEvents.forEach(event => {
            const startDate = new Date(event.start);
            const endDate = new Date(event.end);

            const dateStr = startDate.toISOString().split('T')[0];
            const dayColumn = document.querySelector(`.day-column[data-date="${dateStr}"]`);

            if (!dayColumn) return;

            const startHour = startDate.getHours();
            const startMinutes = startDate.getMinutes();
            const endHour = endDate.getHours();
            const endMinutes = endDate.getMinutes();

            const duration = (endHour - startHour) + (endMinutes - startMinutes) / 60;
            const topOffset = ((startHour - 6) * 60 + startMinutes);

            const eventBlock = document.createElement('div');
            eventBlock.className = 'event-block';
            eventBlock.style.top = `${topOffset}px`;
            eventBlock.style.height = `${duration * 60}px`;

            eventBlock.innerHTML = `
                <div class="event-title">${event.title}</div>
                <div class="event-time-range">
                    ${formatTime(startDate)} - ${formatTime(endDate)}
                </div>
            `;

            dayColumn.appendChild(eventBlock);
        });
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
    // INITIALIZE
    // =============================================================================

    renderMiniCalendar();
    renderWeekEvents();
});