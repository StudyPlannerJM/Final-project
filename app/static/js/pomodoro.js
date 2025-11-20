document.addEventListener('DOMContentLoaded', () => {
    const timerDisplay = document.getElementById('timer-display');
    const startBtn = document.getElementById('start-timer');
    const pauseBtn = document.getElementById('pause-timer');
    const resetBtn = document.getElementById('reset-timer');
    const sessionCountSpan = document.getElementById('session-count');
    const timerStatusSpan = document.getElementById('timer-status');
    const time25Btn = document.getElementById('time-25');
    const time45Btn = document.getElementById('time-45');
    const time60Btn = document.getElementById('time-60');

    let timer;
    let isRunning = false;
    let workDuration = 25 * 60; // Default 25 minutes in seconds
    let timeLeft = workDuration;
    let sessionCount = 0;
    let isBreak = false;

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
    time25Btn.addEventListener('click', () => setWorkDuration(25));
    time45Btn.addEventListener('click', () => setWorkDuration(45));
    time60Btn.addEventListener('click', () => setWorkDuration(60));

    updateDisplay(); // Initial display
});