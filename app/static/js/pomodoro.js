document.addEventListener('DOMContentLoaded', () => {
    const timerDisplay = document.getElementById('timer-display');
    const startBtn = document.getElementById('start-timer');
    const pauseBtn = document.getElementById('pause-timer');
    const resetBtn = document.getElementById('reset-timer');
    const sessionCountSpan = document.getElementById('session-count');
    const timerStatusSpan = document.getElementById('timer-status');

    let timer;
    let isRunning = false;
    let timeLeft = 25 * 60; // 25 minutes in seconds
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
                    timeLeft = 25 * 60; // 25-minute work session
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
        timeLeft = 25 * 60;
        sessionCount = 0;
        isBreak = false;
        timerStatusSpan.textContent = 'Ready';
        sessionCountSpan.textContent = sessionCount;
        updateDisplay();
    }

    startBtn.addEventListener('click', startTimer);
    pauseBtn.addEventListener('click', pauseTimer);
    resetBtn.addEventListener('click', resetTimer);

    updateDisplay(); // Initial display
});