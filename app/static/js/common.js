document.addEventListener('DOMContentLoaded', () => {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');

    // Theme Toggle (state lives in window.BrainDump, set up in theme_init.html)
    const toggleTheme = () => {
        const next = window.BrainDump.getResolvedTheme() === 'dark' ? 'light' : 'dark';
        window.BrainDump.setTheme(next);
    };
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }

    // Sidebar collapse (desktop only; tablets are icon-only via CSS, phones use the tab bar)
    const desktopQuery = window.matchMedia('(min-width: 1024px)');
    const SIDEBAR_KEY = 'sidebarCollapsed';
    const readCollapsed = () => {
        try { return localStorage.getItem(SIDEBAR_KEY) === '1'; } catch (e) { return false; }
    };
    if (sidebar) {
        sidebar.classList.toggle('collapsed', readCollapsed());
    }
    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener('click', () => {
            if (!desktopQuery.matches) return;
            const collapsed = sidebar.classList.toggle('collapsed');
            try { localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0'); } catch (e) { /* storage blocked */ }
        });
    }

    initSheets(toggleTheme);
    initToasts();

    // Floating Pomodoro Timer Widget (needs localStorage; skip quietly if blocked)
    try {
        initFloatingTimer();
    } catch (e) {
        console.warn('Floating timer unavailable:', e);
    }

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
                    <button type="button" id="floating-pause" class="floating-btn" title="Pause" aria-label="Pause timer"><i class="fas fa-pause" aria-hidden="true"></i></button>
                    <button type="button" id="floating-continue" class="floating-btn" title="Continue" aria-label="Continue timer"><i class="fas fa-play" aria-hidden="true"></i></button>
                    <button type="button" id="floating-close" class="floating-btn" title="Open Pomodoro" aria-label="Open Pomodoro timer"><i class="fas fa-up-right-from-square" aria-hidden="true"></i></button>
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
        if (window.location.pathname.replace(/\/$/, '') === '/pomodoro') {
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
                    status = state.isBreak ? 'Break' : 'Focus';
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

// Bottom sheets opened from the mobile tab bar (Study, More)
function initSheets(toggleTheme) {
    const backdrop = document.querySelector('.sheet-backdrop');
    const triggers = document.querySelectorAll('.bottom-nav__item[aria-controls]');
    if (!backdrop || !triggers.length) return;

    const phoneQuery = window.matchMedia('(max-width: 767.98px)');
    let openSheetEl = null;
    let openTrigger = null;

    const focusable = (sheet) => Array.from(sheet.querySelectorAll('a[href], button:not([disabled])'));

    function closeSheet(restoreFocus = true) {
        if (!openSheetEl) return;
        openSheetEl.hidden = true;
        backdrop.hidden = true;
        document.documentElement.classList.remove('sheet-open');
        openTrigger.setAttribute('aria-expanded', 'false');
        const trigger = openTrigger;
        openSheetEl = null;
        openTrigger = null;
        if (restoreFocus) trigger.focus();
    }

    function openSheet(id, trigger) {
        const sheet = document.getElementById(id);
        if (!sheet) return;
        if (openSheetEl) closeSheet(false);
        sheet.hidden = false;
        backdrop.hidden = false;
        document.documentElement.classList.add('sheet-open');
        trigger.setAttribute('aria-expanded', 'true');
        openSheetEl = sheet;
        openTrigger = trigger;
        const first = focusable(sheet)[0];
        if (first) first.focus();
    }

    triggers.forEach((trigger) => {
        trigger.addEventListener('click', () => {
            const id = trigger.getAttribute('aria-controls');
            if (openSheetEl && openSheetEl.id === id) {
                closeSheet();
            } else {
                openSheet(id, trigger);
            }
        });
    });

    backdrop.addEventListener('click', () => closeSheet());

    document.querySelectorAll('.sheet').forEach((sheet) => {
        sheet.addEventListener('click', (event) => {
            const link = event.target.closest('.sheet__link');
            if (!link) return;
            if (link.dataset.action === 'toggle-theme') {
                toggleTheme();
            } else {
                closeSheet(false);
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (!openSheetEl) return;
        if (event.key === 'Escape') {
            closeSheet();
            return;
        }
        if (event.key !== 'Tab') return;
        const items = focusable(openSheetEl);
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        } else if (!openSheetEl.contains(document.activeElement)) {
            event.preventDefault();
            first.focus();
        }
    });

    const onViewportChange = () => {
        if (!phoneQuery.matches) closeSheet(false);
    };
    if (phoneQuery.addEventListener) {
        phoneQuery.addEventListener('change', onViewportChange);
    } else {
        phoneQuery.addListener(onViewportChange);
    }
}


// Flash messages rendered as dismissible toasts
const TOAST_AUTO_DISMISS_MS = 6000;

function wireToast(toast) {
    const close = toast.querySelector('.toast__close');
    if (close) close.addEventListener('click', () => toast.remove());

    const sticky = toast.classList.contains('toast--danger') || toast.classList.contains('toast--error');
    if (sticky) return;

    let timer = null;
    const start = () => {
        clearTimeout(timer);
        timer = setTimeout(() => toast.remove(), TOAST_AUTO_DISMISS_MS);
    };
    const pause = () => clearTimeout(timer);
    const resumeIfIdle = () => {
        if (!toast.matches(':hover') && !toast.contains(document.activeElement)) start();
    };
    toast.addEventListener('mouseenter', pause);
    toast.addEventListener('mouseleave', resumeIfIdle);
    toast.addEventListener('focusin', pause);
    toast.addEventListener('focusout', () => setTimeout(resumeIfIdle, 0));
    start();
}

function initToasts() {
    document.querySelectorAll('.toast').forEach(wireToast);
}

// Show a toast from JavaScript: BrainDump.toast('Saved', 'success')
function showToast(message, category = 'info') {
    const region = document.querySelector('.toasts');
    if (!region) return null;
    const allowed = ['success', 'danger', 'warning', 'info', 'error'];
    const toast = document.createElement('div');
    toast.className = 'toast toast--' + (allowed.includes(category) ? category : 'info');
    const text = document.createElement('span');
    text.className = 'toast__text';
    text.textContent = message;
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast__close';
    close.setAttribute('aria-label', 'Dismiss');
    close.textContent = '\u00d7';
    toast.append(text, close);
    region.appendChild(toast);
    wireToast(toast);
    return toast;
}

window.BrainDump = window.BrainDump || {};
window.BrainDump.toast = showToast;
