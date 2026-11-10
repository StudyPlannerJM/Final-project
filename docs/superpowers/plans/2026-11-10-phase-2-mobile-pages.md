# Phase 2 Mobile Pages Implementation Plan

**Goal:** Rework the tasks board, schedule, Pomodoro, flashcards and dashboard for phones and move their stylesheets onto the design tokens.

**Spec:** `docs/superpowers/specs/2026-11-10-phase-2-mobile-pages-design.md`

**Execution:** inline in one session, one commit per task, tests first where the behaviour is server-rendered, independent review at the end.

## Global Constraints

- Branch `phase-2-mobile-pages`, stacked on `phase-1-design-system`.
- No models, migrations or new dependencies. Leave the four pre-existing uncommitted files alone.
- New CSS uses tokens only; phone breakpoint is below 768px; 44px touch targets under `@media (pointer: coarse)`.
- Tests: `.venv/bin/python -m pytest -q --no-cov`; lint: `ruff check .`.

## Tasks

1. **Shared toast API** — `BrainDump.toast()` in `common.js`; refactor `initToasts` to reuse it.
2. **Tasks board** — card macro and column loop in `tasks/tasks.html`; overdue flag from the route; `task-move` select and column tabs in `kanban.js`; `kanban.css` rewrite. Tests in `tests/test_pages_mobile.py`.
3. **Schedule** — `calendar/agenda-view.js`; Agenda button and container; default view by width; pushState path fix; remove `html, body` overflow rule; responsive polish.
4. **Pomodoro** — timer-first phone layout; `pomodoro.css` on tokens; floating timer icons.
5. **Flashcards and decks** — `decks.css`, `flashcards.css` on tokens; touch sizes.
6. **Dashboard** — icons instead of emoji; unified stat cards; `dashboard.css` on tokens.
7. **Sweep, review, PR** — re-run the page sweep at five sizes in both themes; independent review; fix; open the PR against `phase-1-design-system`.

## Review Focus

1. Moving a task when the request fails or the session has expired: the card must stay where it was, the select must reset, and the user must be told.
2. A column with many tasks or a task with a very long unbroken title at 320px.
3. Agenda with no events, with only tasks, and with all-day Google events.
4. Rotating or resizing across 768px with the board scrolled to the second column.
5. Pomodoro timer running while the layout changes; the floating widget must not cover the tab bar or the page's primary action.
