document.addEventListener('DOMContentLoaded', () => {
    const timerDisplay = document.getElementById('timer-display');
    
    // Only run timer code if we're on the pomodoro timer page
    if (timerDisplay) {
        const startBtn = document.getElementById('start-timer');
        const pauseBtn = document.getElementById('pause-timer');
        const resetBtn = document.getElementById('reset-timer');
        const sessionCountSpan = document.getElementById('session-count');
        const timerStatusSpan = document.getElementById('timer-status');
        const time25Btn = document.getElementById('time-25');
        const time45Btn = document.getElementById('time-45');
        const time60Btn = document.getElementById('time-60');
        const customTimeInput = document.getElementById('custom-time-input');
        const setCustomTimeBtn = document.getElementById('set-custom-time');
        const sessionCompleteSound = document.getElementById('session-complete-sound');

    let timer;
    let isRunning = false;
    let workDuration = 25 * 60; // Default 25 minutes in seconds
    let timeLeft = workDuration;
    let sessionCount = 0;
    let isBreak = false;
    let currentSessionDuration = 25; // Track the actual duration for current session in minutes
    let endTime = null; // Track when timer should end

    // Restore timer state from localStorage
    function restoreTimerState() {
        const savedState = localStorage.getItem('pomodoroState');
        if (savedState) {
            const state = JSON.parse(savedState);
            workDuration = state.workDuration;
            sessionCount = state.sessionCount;
            isBreak = state.isBreak;
            currentSessionDuration = state.currentSessionDuration;
            
            if (state.isRunning && state.endTime) {
                // Calculate remaining time based on end timestamp
                const now = Date.now();
                const remaining = Math.floor((state.endTime - now) / 1000);
                
                if (remaining > 0) {
                    timeLeft = remaining;
                    endTime = state.endTime;
                    startTimer();
                } else {
                    // Timer expired while away - handle completion
                    timeLeft = 0;
                    handleTimerComplete();
                }
            } else {
                timeLeft = state.timeLeft;
            }
            
            // Update active button state
            const durationMinutes = workDuration / 60;
            document.querySelectorAll('.btn-time').forEach(btn => btn.classList.remove('active'));
            if (durationMinutes === 25) time25Btn.classList.add('active');
            else if (durationMinutes === 45) time45Btn.classList.add('active');
            else if (durationMinutes === 60) time60Btn.classList.add('active');
        }
        
        if (sessionCountSpan) sessionCountSpan.textContent = sessionCount;
        updateDisplay();
    }

    // Save timer state to localStorage
    function saveTimerState() {
        const state = {
            isRunning,
            workDuration,
            timeLeft,
            sessionCount,
            isBreak,
            currentSessionDuration,
            endTime
        };
        localStorage.setItem('pomodoroState', JSON.stringify(state));
        
        // Trigger event for other pages to update
        window.dispatchEvent(new Event('pomodoroStateChanged'));
    }

    function updateDisplay() {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    function handleTimerComplete() {
        let completionMessage;

        if (sessionCompleteSound) {
            sessionCompleteSound.currentTime = 0;
            sessionCompleteSound.play().catch(error => {
                console.warn('Session complete sound could not be played:', error);
            });
        }

        if (!isBreak) {
            completionMessage = 'Pomodoro session complete! Time for a break.';
            sessionCount++;
            if (sessionCountSpan) sessionCountSpan.textContent = sessionCount;
            
            // Save Pomodoro session to database with the actual session duration
            savePomodoroSession(currentSessionDuration);

            timeLeft = 5 * 60; // 5-minute break
            isBreak = true;
        } else {
            completionMessage = 'Break over! Time to work again.';
            timeLeft = workDuration; // Return to selected work duration
            isBreak = false;
        }
        if (timerStatusSpan) timerStatusSpan.textContent = 'Ready';
        endTime = null;
        saveTimerState();
        updateDisplay();

        // Delay the blocking popup briefly so the sound begins first.
        setTimeout(() => {
            alert(completionMessage);
        }, 150);
    }

    function startTimer() {
        if (isRunning) return;
        isRunning = true;
        
        // Set end time based on current timeLeft
        endTime = Date.now() + (timeLeft * 1000);
        
        if (timerStatusSpan) timerStatusSpan.textContent = isBreak ? 'Break' : 'Working';
        saveTimerState();
        
        timer = setInterval(() => {
            // Calculate time left based on end timestamp for accuracy
            const now = Date.now();
            const remaining = Math.floor((endTime - now) / 1000);
            
            if (remaining <= 0) {
                clearInterval(timer);
                isRunning = false;
                timeLeft = 0;
                handleTimerComplete();
            } else {
                timeLeft = remaining;
                updateDisplay();
                saveTimerState();
            }
        }, 1000);
    }

    function pauseTimer() {
        clearInterval(timer);
        isRunning = false;
        endTime = null;
        if (timerStatusSpan) timerStatusSpan.textContent = 'Paused';
        saveTimerState();
    }

    function resetTimer() {
        clearInterval(timer);
        isRunning = false;
        timeLeft = workDuration;
        sessionCount = 0;
        isBreak = false;
        endTime = null;
        if (timerStatusSpan) timerStatusSpan.textContent = 'Ready';
        if (sessionCountSpan) sessionCountSpan.textContent = sessionCount;
        saveTimerState();
        updateDisplay();
    }

    function setWorkDuration(minutes) {
        if (isRunning) {
            alert('Please pause the timer before changing duration.');
            return;
        }
        workDuration = minutes * 60;
        timeLeft = workDuration;
        currentSessionDuration = minutes; // Track the duration for this session
        isBreak = false;
        if (timerStatusSpan) timerStatusSpan.textContent = 'Ready';
        saveTimerState();
        updateDisplay();
        
        // Update active button state
        document.querySelectorAll('.btn-time').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }

    // Custom time setter
    function setCustomTime() {
        const customMinutes = parseInt(customTimeInput.value);
        
        if (!customMinutes || customMinutes < 1 || customMinutes > 180) {
            alert('Please enter a valid time between 1 and 180 minutes.');
            return;
        }
        
        if (isRunning) {
            alert('Please pause the timer before changing duration.');
            return;
        }
        
        workDuration = customMinutes * 60;
        timeLeft = workDuration;
        currentSessionDuration = customMinutes;
        isBreak = false;
        if (timerStatusSpan) timerStatusSpan.textContent = 'Ready';
        saveTimerState();
        updateDisplay();
        
        // Remove active state from all preset buttons
        document.querySelectorAll('.btn-time').forEach(btn => btn.classList.remove('active'));
        
        // Clear custom input after setting
        customTimeInput.value = '';
    }
    
    // Restore state first
    restoreTimerState();
    
    if (startBtn) startBtn.addEventListener('click', startTimer);
    if (pauseBtn) pauseBtn.addEventListener('click', pauseTimer);
    if (resetBtn) resetBtn.addEventListener('click', resetTimer);
    if (time25Btn) time25Btn.addEventListener('click', () => setWorkDuration(25));
    if (time45Btn) time45Btn.addEventListener('click', () => setWorkDuration(45));
    if (time60Btn) time60Btn.addEventListener('click', () => setWorkDuration(60));
    if (setCustomTimeBtn) setCustomTimeBtn.addEventListener('click', setCustomTime);
    if (customTimeInput) {
        customTimeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                setCustomTime();
            }
        });
    }

    // Function to save completed Pomodoro session to database
    function savePomodoroSession(durationMinutes) {
        fetch('/pomodoro/api/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                duration: durationMinutes,
                completed: true,
                task_id: null  // Can add task selection later
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Optional: Show success notification
                showNotification(`Great job! You've studied ${data.total_minutes_today} minutes today!`);
            } else {
                console.error('Failed to save Pomodoro:', data.error);
            }
        })
        .catch(error => {
            console.error('Error saving Pomodoro:', error);
        });
    }

    // Function to show temporary notification
    function showNotification(message) {
        const notification = document.createElement('div');
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.backgroundColor = '#28a745';
        notification.style.color = 'white';
        notification.style.padding = '15px 20px';
        notification.style.borderRadius = '8px';
        notification.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
        notification.style.zIndex = '9999';
        notification.style.fontSize = '14px';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.5s';
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }
    
    } // End of timer-specific code

    // Handle delete button clicks for session history (works on all pages)
    let sessionToDelete = null;
    
    function initDeleteButtons() {
        const deleteButtons = document.querySelectorAll('.btn-delete-session');
        
        deleteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                sessionToDelete = this.getAttribute('data-session-id');
                showDeleteModal();
            });
        });
        
        // Set up confirm delete button
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', function() {
                if (sessionToDelete) {
                    deleteSession(sessionToDelete);
                }
            });
        }
        
        // Close modal when clicking overlay
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.addEventListener('click', function(event) {
                if (event.target === modal) {
                    closeDeleteModal();
                }
            });
        }
    }
    
    function showDeleteModal() {
        // Set custom message for session deletion
        const messageEl = document.getElementById('deleteModalMessage');
        if (messageEl) {
            messageEl.textContent = 'Are you sure you want to delete this session?';
        }
        
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }
    
    window.closeDeleteModal = function() {
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.style.display = 'none';
        }
        sessionToDelete = null;
    }

    function deleteSession(sessionId) {
        fetch(`/pomodoro/api/delete/${sessionId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Close modal and reload the page to show updated list
                closeDeleteModal();
                window.location.reload();
            } else {
                closeDeleteModal();
                alert('Error deleting session: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            closeDeleteModal();
            alert('Failed to delete session. Please try again.');
        });
    }

    // Initialize delete buttons if they exist on the page
    initDeleteButtons();
});