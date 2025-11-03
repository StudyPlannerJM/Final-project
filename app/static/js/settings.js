document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.querySelectorAll('.settings-nav a');
    const sections = document.querySelectorAll('.settings-section');
    const themeSelect = document.getElementById('theme-select');
    const body = document.body;

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

    // Theme selector logic
    if (themeSelect) {
        // Set initial value from localStorage
        const currentTheme = localStorage.getItem('theme') || 'light';
        themeSelect.value = currentTheme;

        themeSelect.addEventListener('change', (e) => {
            const selectedTheme = e.target.value;
            body.classList.remove('light-theme', 'dark-theme');
            if (selectedTheme === 'dark') {
                body.classList.add('dark-theme');
            } else {
                body.classList.remove('dark-theme'); // Or add 'light-theme' if you have specific light styles
            }
            localStorage.setItem('theme', selectedTheme);
        });
    }
});