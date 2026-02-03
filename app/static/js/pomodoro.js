document.addEventListener('DOMContentLoaded', () => {
    const timerDisplay = document.getElementById('timer-display');
    const startBtn = document.getElementById('start-timer');
    const pauseBtn = document.getElementById('pause-timer');
    const resetBtn = document.getElementById('reset-timer');
    const sessionCountSpan = document.getElementById('session-count');
    const timerStatusSpan = document.getElementById('timer-status');
    const time1Btn = document.getElementById('time-1');
    const time25Btn = document.getElementById('time-25');
    const time45Btn = document.getElementById('time-45');
    const time60Btn = document.getElementById('time-60');

    let timer;
    let isRunning = false;
    let workDuration = 25 * 60; // Default 25 minutes in seconds
    let timeLeft = workDuration;
    let sessionCount = 0;
    let isBreak = false;
    let currentSessionDuration = 25; // Track the actual duration for current session in minutes

    function updateDisplay() {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    function startTimer() {
        if (isRunning) return;
        isRunning = true;
        timerStatusSpan.textContent = isBreak ? 'Break' : 'Working';
        timer = setInterval(() => {
            timeLeft--;
            updateDisplay();
            if (timeLeft <= 0) {
                clearInterval(timer);
                isRunning = false;
                if (!isBreak) {
                    sessionCount++;
                    sessionCountSpan.textContent = sessionCount;
                    
                    // Save Pomodoro session to database with the actual session duration
                    savePomodoroSession(currentSessionDuration);
                    
                    alert('Pomodoro session complete! Time for a break.');
                    timeLeft = 5 * 60; // 5-minute break
                    isBreak = true;
                } else {
                    alert('Break over! Time to work again.');
                    timeLeft = workDuration; // Return to selected work duration
                    isBreak = false;
                }
                timerStatusSpan.textContent = 'Ready';
                updateDisplay();
            }
        }, 1000);
    }

    function pauseTimer() {
        clearInterval(timer);
        isRunning = false;
        timerStatusSpan.textContent = 'Paused';
    }

    function resetTimer() {
        clearInterval(timer);
        isRunning = false;
        timeLeft = workDuration;
        sessionCount = 0;
        isBreak = false;
        timerStatusSpan.textContent = 'Ready';
        sessionCountSpan.textContent = sessionCount;
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
        timerStatusSpan.textContent = 'Ready';
        updateDisplay();
        
        // Update active button state
        document.querySelectorAll('.btn-time').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }

    startBtn.addEventListener('click', startTimer);
    pauseBtn.addEventListener('click', pauseTimer);
    resetBtn.addEventListener('click', resetTimer);
    time1Btn.addEventListener('click', () => setWorkDuration(1));
    time25Btn.addEventListener('click', () => setWorkDuration(25));
    time45Btn.addEventListener('click', () => setWorkDuration(45));
    time60Btn.addEventListener('click', () => setWorkDuration(60));

    updateDisplay(); // Initial display

    // Function to save completed Pomodoro session to database
    function savePomodoroSession(durationMinutes) {
        fetch('/api/pomodoro/complete', {
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
                console.log('Pomodoro saved successfully!');
                console.log(`Total study time today: ${data.total_minutes_today} minutes`);
                
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
});