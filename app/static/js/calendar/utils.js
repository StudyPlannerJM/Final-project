// =============================================================================
// CALENDAR UTILITIES
// Shared helper functions used across calendar modules
// =============================================================================

import { HOURS_FOR_12H_FORMAT } from './constants.js';

/**
 * Format a Date object as 12-hour time string
 * @param {Date} date - The date to format
 * @returns {string} Formatted time (e.g., "2:30 PM")
 */
export function formatTime(date) {
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= HOURS_FOR_12H_FORMAT ? 'PM' : 'AM';
    const displayHours = hours % HOURS_FOR_12H_FORMAT || HOURS_FOR_12H_FORMAT;
    return `${displayHours}:${String(minutes).padStart(2, '0')} ${ampm}`;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML string
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get color for a category
 * @param {Object|string} category - Category object or string
 * @returns {string} Hex color code
 */
export function getCategoryColor(category) {
    // Handle new category object format
    if (category && typeof category === 'object' && category.color) {
        return category.color;
    }

    // Fallback for old string format or default
    const colors = {
        'Work': '#4285f4',
        'Personal': '#ea4335',
        'Study': '#fbbc04',
        'Health': '#34a853',
        'Other': '#9e9e9e'
    };
    return colors[category] || colors['Other'];
}

/**
 * Get month names array
 * @returns {string[]} Array of month names
 */
export function getMonthNames() {
    return ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
}

/**
 * Get day names array
 * @returns {string[]} Array of day names
 */
export function getDayNames() {
    return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
}
