/**
 * Custom Date / Time Picker
 * Enhances native date, time, and datetime-local inputs with a branded
 * BrainDump popup that includes Clear, Cancel and an OK confirm button.
 *
 * Usage: include this script on any page with date/time inputs.
 * All <input type="date|time|datetime-local"> are enhanced automatically.
 */
(function () {
    'use strict';

    const ICON_MAP = {
        'date': 'fas fa-calendar-alt',
        'time': 'fas fa-clock',
        'datetime-local': 'fas fa-calendar-check',
    };

    // ── Helpers ──────────────────────────────────────────────────────────────

    function formatValue(type, value) {
        if (!value) return '';
        try {
            if (type === 'datetime-local') {
                const d = new Date(value);
                const datePart = d.toLocaleDateString('en-US', {
                    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
                });
                const timePart = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                return `${datePart} • ${timePart}`;
            }
            if (type === 'date') {
                const d = new Date(value + 'T00:00:00');
                return d.toLocaleDateString('en-US', {
                    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
                });
            }
            if (type === 'time') {
                const [h, m] = value.split(':');
                const d = new Date();
                d.setHours(+h, +m, 0, 0);
                return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            }
        } catch (_) { /* fall through */ }
        return value;
    }

    function getPlaceholder(type) {
        return {
            'datetime-local': 'Select date & time…',
            'date': 'Select date…',
            'time': 'Select time…',
        }[type] || 'Select…';
    }

    function getLabelText(input) {
        if (input.id) {
            const lbl = document.querySelector(`label[for="${input.id}"]`);
            if (lbl) return lbl.textContent.trim().replace(/:$/, '');
        }
        return input.name || 'Select';
    }

    function setTriggerDisplay(trigger, type, value) {
        const textEl = trigger.querySelector('.dp-trigger-text');
        const formatted = formatValue(type, value);
        textEl.textContent = formatted || getPlaceholder(type);
        textEl.classList.toggle('dp-has-value', !!formatted);
    }

    // ── Core enhancer ─────────────────────────────────────────────────────────

    function enhanceInput(nativeInput) {
        // Skip if already enhanced or inside a popup
        if (nativeInput.classList.contains('dp-native-hidden') ||
            nativeInput.classList.contains('dp-temp-input')) return;

        const type = nativeInput.type;
        const iconClass = ICON_MAP[type] || 'fas fa-calendar-alt';
        const required = nativeInput.required;

        // ── Wrapper ──
        const wrapper = document.createElement('div');
        wrapper.className = 'dp-wrapper';
        nativeInput.parentNode.insertBefore(wrapper, nativeInput);
        wrapper.appendChild(nativeInput);
        nativeInput.classList.add('dp-native-hidden');
        // Required attribute moves to the trigger so the form still validates
        if (required) nativeInput.removeAttribute('required');

        // Intercept programmatic .value = assignments to keep display in sync
        const proto = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
        Object.defineProperty(nativeInput, 'value', {
            get() { return proto.get.call(this); },
            set(v) {
                proto.set.call(this, v);
                if (triggerBtn) setTriggerDisplay(triggerBtn, type, v);
            },
            configurable: true,
        });

        // ── Trigger button ──
        const triggerBtn = document.createElement('button');
        triggerBtn.type = 'button';
        triggerBtn.className = 'dp-trigger';
        triggerBtn.innerHTML = `
            <span class="dp-trigger-icon"><i class="${iconClass}"></i></span>
            <span class="dp-trigger-text"></span>
            <i class="fas fa-chevron-down dp-trigger-caret"></i>
        `;
        setTriggerDisplay(triggerBtn, type, nativeInput.value);
        wrapper.appendChild(triggerBtn);

        // ── Popup — appended to <body> so it's never clipped by overflow containers ──
        const popup = document.createElement('div');
        popup.className = 'dp-popup';
        popup.innerHTML = `
            <div class="dp-popup-inner">
                <p class="dp-popup-label"><i class="${iconClass}"></i> ${getLabelText(nativeInput)}</p>
                <input class="dp-temp-input" type="${type}">
                <div class="dp-popup-actions">
                    <button type="button" class="dp-btn-clear">Clear</button>
                    <div class="dp-right">
                        <button type="button" class="dp-btn-cancel">Cancel</button>
                        <button type="button" class="dp-btn-ok">
                            <i class="fas fa-check"></i> OK
                        </button>
                    </div>
                </div>
            </div>
        `;
        // Use fixed positioning so the popup escapes any overflow:hidden/auto ancestor
        popup.style.position = 'fixed';
        popup.style.zIndex = '9999';
        document.body.appendChild(popup);

        const tempInput = popup.querySelector('.dp-temp-input');

        // ── Position popup below the trigger button ──
        function repositionPopup() {
            const rect = triggerBtn.getBoundingClientRect();
            const popupHeight = popup.offsetHeight || 200;
            const spaceBelow = window.innerHeight - rect.bottom;
            const spaceAbove = rect.top;
            // Open above if not enough space below
            if (spaceBelow < popupHeight + 10 && spaceAbove > popupHeight + 10) {
                popup.style.top  = (rect.top - popupHeight - 6) + 'px';
            } else {
                popup.style.top  = (rect.bottom + 6) + 'px';
            }
            // Align left edge with trigger, but keep within viewport
            let left = rect.left;
            const popupWidth = popup.offsetWidth || 240;
            if (left + popupWidth > window.innerWidth - 8) {
                left = window.innerWidth - popupWidth - 8;
            }
            popup.style.left = Math.max(8, left) + 'px';
            popup.style.width = Math.max(rect.width, 240) + 'px';
        }

        // ── Open / close helpers ──
        function openPopup() {
            // Close any other open pickers
            document.querySelectorAll('.dp-popup.dp-open').forEach(p => {
                p.classList.remove('dp-open');
            });
            document.querySelectorAll('.dp-trigger.dp-open').forEach(t => {
                t.classList.remove('dp-open');
            });

            tempInput.value = nativeInput.value || '';
            popup.classList.add('dp-open');
            triggerBtn.classList.add('dp-open');
            repositionPopup();
            setTimeout(() => tempInput.focus(), 50);
        }

        function closePopup() {
            popup.classList.remove('dp-open');
            triggerBtn.classList.remove('dp-open');
        }

        // ── Event listeners ──
        triggerBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            popup.classList.contains('dp-open') ? closePopup() : openPopup();
        });

        popup.querySelector('.dp-btn-ok').addEventListener('click', function () {
            nativeInput.value = tempInput.value;  // triggers the intercepted setter → updates display
            nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
            closePopup();
        });

        popup.querySelector('.dp-btn-cancel').addEventListener('click', closePopup);

        popup.querySelector('.dp-btn-clear').addEventListener('click', function () {
            tempInput.value = '';
            nativeInput.value = '';
            nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
            closePopup();
        });

        // Close when clicking outside
        document.addEventListener('click', function (e) {
            if (!wrapper.contains(e.target) && !popup.contains(e.target)) closePopup();
        });

        // Close if anything scrolls (popup is fixed so it'd float away otherwise)
        window.addEventListener('scroll', closePopup, { passive: true, capture: true });

        // Sync display when the parent form is reset (e.g. after modal close)
        const parentForm = nativeInput.form || nativeInput.closest('form');
        if (parentForm) {
            parentForm.addEventListener('reset', function () {
                setTimeout(() => setTriggerDisplay(triggerBtn, type, nativeInput.value), 0);
            });
        }
    }

    // ── Init ──────────────────────────────────────────────────────────────────

    function init() {
        document.querySelectorAll(
            'input[type="datetime-local"], input[type="date"], input[type="time"]'
        ).forEach(enhanceInput);
    }

    // Always defer to DOMContentLoaded so all other deferred/module scripts
    // (e.g. schedule.js) have already wired up DOM cache before we wrap inputs.
    document.addEventListener('DOMContentLoaded', init);
})();
