# Phase 3 Retention Implementation Plan

**Goal:** Spaced repetition with a review session, a dashboard that shows what to do today, and an installable app with an offline page.

**Spec:** `docs/superpowers/specs/2026-11-11-phase-3-retention-design.md`

**Execution:** inline, tests first, one commit per task, independent review at the end.

## Global Constraints

- Branch `phase-3-retention`, stacked on `phase-2-mobile-pages`.
- One new Alembic migration; additive only. No new Python dependencies.
- Timestamps stored in UTC; calendar days computed in the user's timezone.
- New CSS uses tokens only; 44px touch targets; both themes.
- Leave the four pre-existing uncommitted files alone; stage by explicit path.

## Tasks

1. **Scheduler and data** — `Flashcard` columns, `CardReview` model, migration, `review_service.schedule()` and `ReviewService` (due queries, record review, stage counts).
2. **Timezone helper** — `app/utils/timezone.py`, cookie set in the theme bootstrap script.
3. **Review session** — routes, `flashcards/review.html`, `review.js`, `review.css`, entry points.
4. **Dashboard** — `stats_service.py`, Today panel, streak, weekly chart, deck progress.
5. **Installable app** — manifest, `/sw.js`, `/offline`, registration.
6. **Sweep, review, PR.**

## Review Focus

1. A card deleted or moved while a review session is open in another tab.
2. Rating the same card twice quickly (double tap) or replaying the request.
3. A user with thousands of cards or reviews: page weight and query count on the dashboard.
4. Timezone cookie missing, malformed or hostile; day boundaries around midnight and DST.
5. The service worker serving a stale or wrong page after logout, after a deploy, or for non-GET requests.
