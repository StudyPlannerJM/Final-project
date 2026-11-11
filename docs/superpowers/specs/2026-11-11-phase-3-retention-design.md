# Phase 3: features that bring students back

Date: 2026-11-11
Status: design choices approved in chat (review session; all four dashboard
additions; install plus offline page). Stacked on Phase 2.

## Purpose

Phases 1 and 2 made the app pleasant on a phone. Phase 3 adds the reasons to
open it every day: flashcards that come back when they are about to be
forgotten, a dashboard that says what to do today, and a home-screen app.

## Success criteria

- A student can review the cards that are due, one at a time, rate each, and
  the next due date changes accordingly.
- The dashboard answers "what should I do today?" without navigating.
- The app can be installed to the home screen and shows a friendly page when
  opened offline.
- Day boundaries (today, streak, weekly chart) follow the student's own
  timezone, not the server's.
- Existing data keeps working: cards created before this phase are "new" and
  due immediately.

## Spaced repetition

### Data

`flashcard` gains: `due_at` (DateTime, null = never reviewed, due now),
`interval_days` (Integer, default 0), `ease` (Float, default 2.5), `reps`
(Integer, default 0), `lapses` (Integer, default 0), `last_reviewed_at`
(DateTime, null).

New table `card_review`: `id`, `user_id`, `flashcard_id` (deleted with the
card), `rating` (0-3), `reviewed_at` (UTC). It is the log used for streaks.

One Alembic migration adds both. All timestamps are stored in UTC.

### Scheduler

A pure function `schedule(state, rating, now)` in
`app/services/review_service.py`, a simplified SM-2:

| Rating | Effect |
|---|---|
| Again (0) | reps 0, lapses +1, ease −0.20, due in 10 minutes |
| Hard (1) | interval 1 day if new, else ×1.2 (at least +1 day); ease −0.15 |
| Good (2) | interval 1 day, then 3 days, then ×ease |
| Easy (3) | interval 4 days if new, else ×ease×1.3; ease +0.15 |

Ease never drops below 1.3; interval is capped at 365 days. A card is due
when `due_at` is null or in the past.

Stages for display: **new** (never reviewed), **learning** (interval under
21 days), **mastered** (21 days or more).

### Review session

- `GET /flashcards/review` (optional `deck_id`): up to 50 due cards, oldest
  due first, never-reviewed cards after overdue ones.
- One card at a time: question, "Show answer", then four rating buttons, each
  showing the interval it would give. Progress bar and count.
- `POST /flashcards/review/<card_id>` with `{rating}` records the review and
  returns the new due date. Only the card's owner may post. The request must
  carry the CSRF token.
- A card rated Again returns at the end of the same session.
- Keyboard: Space or Enter reveals; 1-4 rate.
- End of session: summary by rating and a link back. With nothing due: "All
  caught up" and when the next card is due.
- If saving a rating fails, the card stays on screen and a toast says so.
- Entry points: "Review due cards" on the flashcards pages (with the count)
  and the dashboard Today panel.

## Timezone

The browser stores its IANA timezone name in a `bd_tz` cookie. The server
reads it (falling back to UTC if missing or invalid) through
`app/utils/timezone.py` and uses it wherever a calendar day matters.

## Dashboard

Order: Today, quick actions, streak and weekly chart, deck progress, then the
existing counts and recent tasks.

- **Today panel**: open tasks that are overdue or due today (up to 5, with a
  link to the board), and the number of cards due with a "Review now"
  button. Friendly empty states.
- **Study streak**: consecutive local days with a completed Pomodoro or at
  least one card review. Today not yet active does not break the streak.
  Shows current and longest.
- **Weekly study chart**: study minutes per day for the last 7 local days as
  CSS bars with visible values and a text alternative.
- **Deck progress**: per deck, a stacked bar of new / learning / mastered and
  the number due.

Statistics live in `app/services/stats_service.py`.

## Installable app

- Manifest: name, description, `id`, colours, icons marked `any` and
  `maskable`.
- `GET /sw.js` serves the service worker from the site root so it controls
  the whole app. It pre-caches only the offline page and its static assets.
  Navigations go to the network first; if that fails, the offline page is
  shown. No authenticated page or API response is ever cached.
- `GET /offline`: a small public page ("You're offline") with a retry button.
- The service worker is registered from the shared script; a failed
  registration is ignored.

## Testing

- Unit tests for the scheduler (each rating from new and from mature, ease
  floor, interval cap) and for streak, weekly minutes and deck progress with
  fixed clocks and timezones.
- Route tests: review page lists only the user's due cards; posting a rating
  updates the card and logs a review; other users get 404; invalid rating is
  400; dashboard shows the panels; `/sw.js`, `/offline` and the manifest
  respond without login.
- Browser: a full review session on a phone-sized screen, the dashboard in
  both themes, and the offline page.

## Out of scope

Push notifications, offline study, per-user algorithm settings, undo of a
rating, importing decks. CSRF on the pre-existing JSON endpoints, the seeded
admin account and rate limiting remain Phase 4.
