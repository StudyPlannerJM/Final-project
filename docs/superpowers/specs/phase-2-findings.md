# Phase 2 input: findings from the Phase 1 full-page pass

Date: 2026-11-10. Collected while verifying the Phase 1 shell on every page at
320×568, 375×812, 640×360, 768×1024 and 1280×800, in light and dark themes.

## How this was checked

An in-browser script loaded each page at each size and theme and measured:
horizontal overflow, text contrast below 3:1 against solid backgrounds,
interactive controls shorter than 36px on phone widths, fixed elements
colliding with the tab bar, and clipped tab labels. Tasks, Schedule,
Pomodoro, Decks, the delete dialog, Add Task and both auth pages were also
checked by eye on a 375px viewport.

Limits of the check: text placed on gradients or images is not measured;
touch-target sizes were measured without touch emulation, so `.btn` elements
(which grow to 44px on touch devices) show up smaller than they are on a
phone; nothing was tested on a physical device.

## Result for Phase 1 scope

- No horizontal page scroll on any page at any size.
- No text below 3:1 on solid backgrounds in either theme after the fixes below.
- Tab labels fit at 320px. The More sheet scrolls inside a 360px-tall viewport.
- A 30-character username and a long page title do not overflow the header.

Fixed during the pass (they made content unreadable or collided with the shell):

- White text hardcoded on primary-coloured backgrounds, unreadable in dark
  theme (23 rules across pomodoro, schedule, ai-planner, decks, settings,
  summarizer): now `var(--color-on-primary)`.
- Admin users table (`#000` text) and admin form Cancel button (white
  background) in dark theme.
- Date picker placeholder text in light theme.
- Schedule "add event" button sat on top of the tab bar on phones.
- Task and schedule modal overlays were painted under the tab bar.
- Shared delete dialog tokenised.

## Open findings by page

Format: viewport / theme — problem — file and selector.

### Dashboard
- All / both — emoji used as icons in every stat card, heading and quick action (21 occurrences) — `templates/dashboard.html`.
- Phone / both — recent-task edit links are under 36px tall — `a.task-edit-btn`.
- All / both — coloured card borders (yellow, blue, green, purple) are hardcoded and off-palette — `dashboard.css`.

### Tasks (kanban)
- Phone / both — the three columns stack vertically, so the board is a long scroll; needs swipeable columns or a status filter — `kanban.css`.
- All / both — column headers use a hardcoded teal gradient that is off-palette — `kanban.css` (31 hardcoded colours).
- Phone / both — the "Drag tasks between columns" hint does not apply to touch as written.

### Add / edit task
- Phone / both — the hidden native date input is still in the layout (`input#due_date.dp-native-hidden`); harmless but should be removed from the tab order.
- All / both — `date-picker.css` has 28 hardcoded colours and its own dark overrides.

### Schedule
- Phone / both — month title wraps mid-word ("Novem-ber, 2026") next to the view switcher — `schedule-layout.css`.
- Phone / both — the week view squeezes seven columns into the screen; day letters are clipped. Default to day or agenda view on phones.
- Phone / both — view switcher, previous/next and Today buttons are under 36px tall — `button.view-btn`, `button.nav-btn`, `button.today-btn`.

### Pomodoro
- Phone / both — duration presets, custom time, timer and controls are one long column; the timer itself is below the fold on short screens.
- All / dark — Pause (`.btn-secondary`) has almost no visible boundary against the card.
- All / both — `pomodoro.css` is 1,000+ lines with 32 hardcoded colours and a large block of `body.dark-theme` overrides that tokens now make redundant.
- Floating timer widget buttons are emoji (⏸ ☕ 🍅 📚) — `static/js/common.js`.

### Flashcards and decks
- All / dark — deck card header keeps a light gradient in dark theme — `decks.css` (44 hardcoded colours, the most of any file).
- Phone / both — deck icon picker renders about 40 buttons under 36px — `button.icon-btn` in add/edit deck.
- Add/edit deck templates use emoji as icon choices (🌍 🎨 📚 📝 🔢 🔬).
- Study view is a list of flip cards, not a one-card-at-a-time study mode.

### Summarizer and AI planner
- Phone / both — AI planner delete icon button is under 36px — `button.btn-delete-icon`.
- All / both — `.btn-secondary`, `.btn-info` and others are redefined per page in `ai-planner-components.css` instead of using the core buttons.

### Admin
- Phone / both — admin checkbox is small (`input#is_admin`).
- `manage-users.css` (29) and `user-form.css` (17) still carry hardcoded colours with fallback values from an older purple palette.

### Calendar sync prompt
- `calendar-sync-prompt.css` defines its own colour variables (`--sync-*`, 37 hardcoded colours) instead of the tokens.

## Hardcoded colour counts remaining (per stylesheet)

decks 44, calendar-sync-prompt 37, pomodoro 32, kanban 31, admin/manage-users 29,
date-picker 28, admin/user-form 17, flashcards 16, dashboard 15, tasks 12,
schedule-layout 10, schedule-month-view 6, ai-planner (4 files) 15,
summarizer (4 files) 11, settings 3, schedule week/day 2.

## Cross-cutting

- Many page stylesheets keep `body.dark-theme` override blocks that only
  restate colours; these can be deleted as each file moves to tokens.
- Buttons are restyled per page in several places; converge on `core/buttons.css`.
- Font Awesome is still loaded from a CDN; self-host or switch to inline SVG
  when the PWA work starts (offline use).

## From the Phase 1 code review (not fixed in Phase 1)

- No automated test covers shell behaviour in the browser: sheet open/close
  and focus, toast dismissal and timers, the theme toggle and the
  storage-blocked fallback are checked by hand only. The project has no
  JavaScript test runner; adding one (or a small Playwright suite) is the fix.
- The floating Pomodoro timer reads `localStorage` without a guard
  (`static/js/common.js`, `initFloatingTimer`). With storage blocked it throws
  on every page and the task category colours are not applied.
- `user_initial` takes the first code point, so a flag emoji, a decomposed
  accent or a leading zero-width character gives a wrong or empty avatar.
- A toast's auto-dismiss timer can restart on mouse-leave while keyboard focus
  is still inside it.
- Flash messages present at page load may not be announced by screen readers,
  because the live region is rendered with its content already in place.
- `summarizer-components.css` `.btn-primary:hover` uses a hardcoded blue with
  about 4:1 contrast in dark theme.
- The floating Pomodoro widget and the schedule "add event" button share the
  bottom-right corner on phones (pre-existing).

## Left open after Phase 2 (from its code review)

- Overdue, agenda dates and the kanban tabs are browser-side logic with no
  automated tests; the project still has no JavaScript test runner.
- The schedule has no `popstate` handler, so the browser Back button does not
  restore the previous calendar view.
- `showNotification` in `schedule.js` still uses `alert()`.
- On phones a toast and the floating Pomodoro widget can briefly overlap at
  the bottom of the screen.
- Deck indicator colour (`--deck-indicator-color`) is set by `flashcard.js`
  but not used by any stylesheet.
- Not reworked in Phase 2: summarizer, AI planner, admin, settings, date
  picker and calendar sync prompt pages still carry hardcoded colours.
- Nothing has been tested on a physical phone.

## Left open after Phase 3 (from its code review)

- The Pomodoro completion response (`total_minutes_today` in
  `pomodoro_service.py`) still counts the UTC day, while the dashboard now
  counts the user's local day, so the two can differ in the evening.
- Study-plan tasks are created with UTC due dates (`study_plan_service.py`)
  but the dashboard treats task due dates as local wall-clock time, so those
  tasks can show as overdue or "today" a few hours early or late.
- The manifest has no `maskable` icons; Android shows the icon on a plain
  disc. Needs a padded icon asset.
- The service worker cache name is fixed (`braindump-offline-v1`); a change to
  the offline page's CSS alone is only picked up when `sw.js` changes.
- The rating replay check is not atomic: two tabs rating the same card at the
  same instant could both be recorded.
- PWA tests read source text; nothing loads every pre-cached URL in a test.
