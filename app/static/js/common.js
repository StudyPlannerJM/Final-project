document.addEventListener('DOMContentLoaded', () => {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const body = document.body;
    const sidebar = document.querySelector('.sidebar');
    const mobileBreakpoint = window.matchMedia('(max-width: 768px)');

    // Theme Toggle (state lives in window.BrainDump, set up in theme_init.html)
    const toggleTheme = () => {
        const next = window.BrainDump.getResolvedTheme() === 'dark' ? 'light' : 'dark';
        window.BrainDump.setTheme(next);
    };
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }

    // Sidebar Toggle
    if (sidebarToggleBtn && sidebar) {
        const closeMobileSidebar = () => {
            sidebar.classList.remove('open');
            body.classList.remove('sidebar-open');
        };

        const syncSidebarMode = () => {
            if (mobileBreakpoint.matches) {
                sidebar.classList.remove('collapsed');
            } else {
                closeMobileSidebar();
            }
        };

        sidebarToggleBtn.addEventListener('click', () => {
            if (mobileBreakpoint.matches) {
                const isOpen = sidebar.classList.toggle('open');
                body.classList.toggle('sidebar-open', isOpen);
            } else {
                sidebar.classList.toggle('collapsed');
            }
        });

        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', closeMobileSidebar);
        }

        sidebar.querySelectorAll('.nav-link').forEach((link) => {
            link.addEventListener('click', () => {
                if (mobileBreakpoint.matches) {
                    closeMobileSidebar();
                }
            });
        });

        if (mobileBreakpoint.addEventListener) {
            mobileBreakpoint.addEventListener('change', syncSidebarMode);
        } else {
            mobileBreakpoint.addListener(syncSidebarMode);
        }

        syncSidebarMode();
    }

    // Floating Pomodoro Timer Widget
    initFloatingTimer();

    // Apply task category colors from data attributes.
    document.querySelectorAll('.task-category[data-category-color]').forEach((categoryBadge) => {
        const color = categoryBadge.getAttribute('data-category-color');
        if (color) {
            categoryBadge.style.setProperty('--category-color', color);
        }
    });
});

function initFloatingTimer() {
    let floatingTimer = null;
    let updateInterval = null;

    function createFloatingTimer() {
        if (floatingTimer) return;

        floatingTimer = document.createElement('div');
        floatingTimer.id = 'floating-pomodoro';
        floatingTimer.innerHTML = `
            <div class="floating-timer-content">
                <div class="floating-timer-display">--:--</div>
                <div class="floating-timer-status">Ready</div>
                <div class="floating-timer-actions">
                    <button id="floating-pause" class="floating-btn" title="Pause">⏸</button>
                    <button id="floating-continue" class="floating-btn" title="Continue">▶</button>
                    <button id="floating-close" class="floating-btn" title="Go to Pomodoro">🍅</button>
                </div>
            </div>
        `;
        document.body.appendChild(floatingTimer);

        // Add event listeners
        document.getElementById('floating-pause').addEventListener('click', pauseFloatingTimer);
        document.getElementById('floating-continue').addEventListener('click', continueFloatingTimer);
        document.getElementById('floating-close').addEventListener('click', () => {
            window.location.href = '/pomodoro';
        });
    }

    function removeFloatingTimer() {
        if (floatingTimer) {
            floatingTimer.remove();
            floatingTimer = null;
        }
        if (updateInterval) {
            clearInterval(updateInterval);
            updateInterval = null;
        }
    }

    function updateFloatingTimer() {
        const savedState = localStorage.getItem('pomodoroState');
        if (!savedState) {
            removeFloatingTimer();
            return;
        }

        const state = JSON.parse(savedState);
        
        // Don't show floating timer on pomodoro page itself
        if (window.location.pathname === '/pomodoro') {
            removeFloatingTimer();
            return;
        }

        // Show only if timer has started and is running or paused with time left
        let showFloating = false;
        let display = '--:--';
        let status = 'Ready';
        let remaining = 0;
        if (state.hasStarted) {
            if (state.isRunning && state.endTime) {
                // Running
                const now = Date.now();
                remaining = Math.floor((state.endTime - now) / 1000);
                if (remaining > 0) {
                    showFloating = true;
                    const minutes = Math.floor(remaining / 60);
                    const seconds = remaining % 60;
                    display = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                    status = state.isBreak ? '☕ Break' : '📚 Working';
                }
            } else if (!state.isRunning && state.timeLeft > 0) {
                // Paused (even if pause is clicked multiple times)
                showFloating = true;
                remaining = state.timeLeft;
                const minutes = Math.floor(remaining / 60);
                const seconds = remaining % 60;
                display = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                status = 'Paused';
            }
        }

        // Only remove if timer is completed or no time left
        if (showFloating && remaining > 0) {
            createFloatingTimer();
            floatingTimer.querySelector('.floating-timer-display').textContent = display;
            floatingTimer.querySelector('.floating-timer-status').textContent = status;
        } else {
            removeFloatingTimer();
        }
    }

    function pauseFloatingTimer() {
        const savedState = localStorage.getItem('pomodoroState');
        if (!savedState) return;

        const state = JSON.parse(savedState);
        
        // Only recalculate remaining if endTime is set (i.e., not already paused)
        let remaining = state.timeLeft;
        if (state.endTime) {
            const now = Date.now();
            remaining = Math.floor((state.endTime - now) / 1000);
        }
        state.isRunning = false;
        state.timeLeft = remaining > 0 ? remaining : 0;
        state.endTime = null;
        
        localStorage.setItem('pomodoroState', JSON.stringify(state));
        window.dispatchEvent(new Event('pomodoroStateChanged'));
        updateFloatingTimer();
    }

    function continueFloatingTimer() {
        const savedState = localStorage.getItem('pomodoroState');
        if (!savedState) return;

        const state = JSON.parse(savedState);
        
        if (!state.isRunning && state.timeLeft > 0) {
            state.isRunning = true;
            state.endTime = Date.now() + (state.timeLeft * 1000);
            
            localStorage.setItem('pomodoroState', JSON.stringify(state));
            window.dispatchEvent(new Event('pomodoroStateChanged'));
            updateFloatingTimer();
        }
    }

    // Initial check
    updateFloatingTimer();

    // Update every second
    updateInterval = setInterval(updateFloatingTimer, 1000);

    // Listen for storage changes from other tabs/pages
    window.addEventListener('storage', (e) => {
        if (e.key === 'pomodoroState') {
            updateFloatingTimer();
        }
    });

    // Listen for custom event from same page
    window.addEventListener('pomodoroStateChanged', updateFloatingTimer);
}