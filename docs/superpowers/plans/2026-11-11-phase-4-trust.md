# Phase 4 Trust Implementation Plan

**Spec:** `docs/superpowers/specs/2026-11-11-phase-4-trust-design.md`
**Execution:** inline, tests first, one commit per task, independent review at the end.

## Global Constraints

- Branch `phase-4-trust`, stacked on `phase-3-retention`.
- Do not edit `app/config.py`, `run.py` or `requirements.txt` (they hold the user's uncommitted changes); put configuration in `create_app`.
- One additive migration. No new Python dependencies.

## Tasks

1. **CSRF everywhere** — `CSRFProtect`, meta tag, fetch header, hidden fields, POST logout/disconnect, CSRF error responses.
2. **Sign-in protection** — `LoginAttempt` model and migration, limiter service, login route, `next` handling, password length, `ProxyFix` in production.
3. **Error pages and headers** — error template and handlers, `after_request` headers, production cookie flags.
4. **README and CI.**
5. **Sweep, review, PR.**

## Review Focus

1. A page open from before deploy (no meta token) posting after the deploy.
2. Lockout used against a victim: someone repeatedly failing to lock another student out.
3. Requests behind Render's proxy: correct client IP; spoofed `X-Forwarded-For` when not behind a proxy.
4. File upload form (summarizer) and multipart posts with CSRF.
5. An exception inside the 500 handler itself, or during a failed transaction.
