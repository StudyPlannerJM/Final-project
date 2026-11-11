# Phase 2: per-page mobile rework

Date: 2026-11-10
Status: design choices approved in chat (kanban: swipeable columns; schedule:
agenda first on phones; flashcards: keep the list and polish it; delivery:
separate branch and PR stacked on Phase 1).

## Purpose

Phase 1 gave every page the new tokens and shell. The pages themselves are
still desktop layouts squeezed onto phones. Phase 2 reworks the pages that
students use most so they are comfortable one-handed on a phone, and moves
their stylesheets onto the tokens. Input: `phase-2-findings.md`.

No models or migrations change. No new dependencies.

## Success criteria

- At 375px every reworked page is usable without horizontal page scroll, and
  every control on it is at least 44px tall on touch devices.
- Task status can be changed on a phone without drag and drop.
- Schedule opens on an agenda list on phones; week, month and day remain.
- No emoji used as interface icons on the dashboard or in the floating timer.
- Reworked stylesheets contain no hardcoded colours except deliberate
  category/deck colours coming from data.
- Existing tests pass; new behaviour that is server-rendered has tests.

## Shared: toasts from JavaScript

`window.BrainDump.toast(message, category = 'info')` appends a toast to the
`.toasts` region with the same markup and auto-dismiss rules as server
flashes. Message is set with `textContent`. Used instead of `alert()`.

## Tasks board

- Template: the three near-identical column blocks become one loop over
  `(status, label, tasks)` with a card macro.
- Each card gets a "Move to" control: a native `<select class="task-move">`
  listing the other two statuses, labelled for screen readers. Changing it
  calls the existing `POST /tasks/update_status/<id>/<status>` and moves the
  card. Works on all screen sizes and with a keyboard.
- Phone (below 768px): the board is a horizontal scroll-snap strip, one column
  per screen. Above it, three tabs (To-Do, Doing, Done) with live counts show
  and set the visible column. Custom touch drag is disabled at this width
  because it fights horizontal swiping; desktop drag and drop is unchanged.
- Empty columns show "No tasks here yet".
- Overdue due dates (past, status not done) are marked with the danger colour
  and an "Overdue" label; this is decided server-side.
- Failures show a toast instead of `alert()`.
- `kanban.css` rewritten on tokens; column headers lose the teal gradient.

## Schedule

- New view `agenda`: the next 7 days from today, grouped by day, each item
  showing time, title, and for tasks their status. Tapping an item opens the
  existing task or event dialog. Days with nothing are omitted; if the whole
  range is empty a friendly empty state is shown. Data comes from the existing
  `view=upcoming` API.
- View switcher gains an Agenda button. Default view: `agenda` below 768px,
  `week` otherwise, unless the URL names a view. Previous/next arrows are
  hidden in agenda view; Today stays.
- Fix: navigation pushed `/schedule?...` into history, which is not a real
  route (`/calendar/schedule`); it now keeps the current path.
- Fix: `schedule-responsive.css` set overflow on `html, body`, which breaks
  the sticky header on this page; removed.
- Header title stays on one line; switcher and navigation controls are 44px
  on touch devices.

## Pomodoro

- Phone layout is timer first: time display and Start/Pause/Reset at the top,
  duration presets as a single row of chips, custom time below, then session
  info.
- `pomodoro.css` moved to tokens; redundant `body.dark-theme` blocks deleted.
- Floating timer buttons use Font Awesome icons with `aria-label`s.

## Flashcards and decks

- Keep the existing list of flip cards.
- Decks: header uses the deck colour on a surface that works in both themes;
  action buttons use the core button styles; icon picker buttons are 44px.
- Flashcards list: cards, toolbar and empty state on tokens; controls 44px.
- `decks.css` and `flashcards.css` moved to tokens.

## Dashboard

- Emoji replaced by Font Awesome icons in tinted circles; stat cards share one
  style with a small colour accent per group; headings lose emoji.
- "Recent tasks" edit links become 44px targets.
- Layout otherwise unchanged (the richer dashboard is Phase 3).

## Testing

- pytest: card macro renders the move control with the two other statuses;
  overdue marking; agenda button and container present; no emoji in the
  dashboard template output; no stylesheet sets overflow on `body`; reworked
  stylesheets contain no hardcoded hex colours.
- Browser: the Phase 1 sweep script re-run on all pages, plus manual checks of
  moving a task on a phone, agenda rendering, and the Pomodoro layout.

## Out of scope

Spaced repetition, one-card study mode, dashboard charts and streaks, PWA
(Phase 3). CSRF on JSON endpoints, seeded admin account, rate limiting
(Phase 4). Summarizer, AI planner, admin and settings pages beyond what they
already inherit.
