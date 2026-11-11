document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.querySelectorAll('.settings-nav a');
    const sections = document.querySelectorAll('.settings-section');
    const themeSelect = document.getElementById('theme-select');

    // Settings navigation
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            navLinks.forEach(navLink => navLink.classList.remove('active'));
            sections.forEach(section => section.classList.remove('active'));

            link.classList.add('active');
            const targetSection = document.querySelector(link.getAttribute('href'));
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });

    // Theme selector (state lives in window.BrainDump, set up in theme_init.html)
    if (themeSelect && window.BrainDump) {
        themeSelect.value = window.BrainDump.getThemePreference();
        themeSelect.addEventListener('change', (e) => {
            window.BrainDump.setTheme(e.target.value);
        });
    }
});
