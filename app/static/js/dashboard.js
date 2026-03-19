document.addEventListener('DOMContentLoaded', () => {
    const mobileBreakpoint = window.matchMedia('(max-width: 768px)');
    const statCards = document.querySelectorAll('.stats-grid .stat-card');
    if (!statCards.length) return;

    // Derive the tasks URL from the sidebar navigation link if present
    const tasksNavLink = document.querySelector('a.nav-link[href*="/tasks"]');
    const tasksUrl = tasksNavLink ? tasksNavLink.href : (window.location.origin + '/tasks');

    function isInteractive(el) {
        return Boolean(el.closest && el.closest('a, button, input, textarea, select, label'));
    }

    statCards.forEach((card) => {
        card.addEventListener('click', (e) => {
            if (!mobileBreakpoint.matches) return; // only on mobile
            if (isInteractive(e.target)) return; // ignore clicks on interactive children

            // Navigate to tasks index
            window.location.href = tasksUrl;
        });
    });
});
