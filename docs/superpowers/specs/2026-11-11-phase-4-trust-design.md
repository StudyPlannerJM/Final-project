# Phase 4: reliability and trust

Date: 2026-11-11
Status: scope approved in chat (all four areas; database table for sign-in
limits). Stacked on Phase 3.

## Purpose

Before classmates hold real accounts, close the gaps a careful reviewer would
find first: forged requests, password guessing, raw error pages, and a
project that is hard to read on GitHub and only checked by CI on `main`.

## Findings that drive this phase

- No app-wide CSRF protection. Ten templates post forms without a token, and
  the JavaScript `POST`/`DELETE` calls (task status, Pomodoro saves and
  deletes, calendar sync, task delete) send none.
- Logout and Google Calendar disconnect change state on a `GET` link.
- Unlimited sign-in attempts; registration accepts any password length.
- No error handlers: 404, 403, 500 and CSRF failures show Flask's bare pages.
- README is UTF-16 and unreadable on GitHub; CI runs only for pull requests
  into `main`, on Python 3.10 while Render uses 3.11, with ruff unpinned.
- Production seeding of the default accounts is already off on Render
  (`SEED_DEFAULT_USERS_PRODUCTION: "false"` on `main`); not changed here.

## CSRF

- `CSRFProtect` enabled for the whole app. Tests keep it off by default and
  turn it on where they check it.
- `<meta name="csrf-token">` in `base.html`. The shared script adds an
  `X-CSRFToken` header to every same-origin non-GET `fetch`, and the two
  scripts that build forms in JavaScript add a hidden `csrf_token` field.
- Every server-rendered `POST` form gets a hidden `csrf_token` field (forms
  using `form.hidden_tag()` already have one).
- Logout and Calendar disconnect become `POST` forms styled as the existing
  links/buttons. A `GET` to either redirects without changing anything.
- A failed CSRF check returns JSON `{success: false, error}` (400) for JSON or
  `fetch` requests and the friendly "session expired" page otherwise.

## Sign-in protection

- New table `login_attempt` (email lowercased, IP, time), one migration.
- A sign-in is refused before the password is checked when, in the last 15
  minutes, there are 5 failures for that email from the same IP, 20 for that
  email from any IP, or 50 from that IP for any email. (Revised after review:
  a plain per-email limit let one student lock a classmate out, and a low
  per-IP limit could block a whole campus network.)
  The message says how long to wait and does not reveal whether the email
  exists.
- A successful sign-in clears that email's failures. Rows older than a day
  are deleted as new failures are written.
- In production the app trusts one proxy hop for the client IP (`ProxyFix`),
  matching Render's load balancer; `PROXY_FIX_X_FOR` overrides it. Blocked
  sign-ins are logged with the address and `X-Forwarded-For` so the setting
  can be checked after deploy.
- Google Calendar's OAuth callback checks the `state` it issued (added after
  review), and insecure OAuth transport is only allowed outside production.
- Registration and the admin user form require at least 8 characters.
- `?next=` is honoured only for same-site relative paths.

## Error pages and headers

- One standalone error template (works signed in or out, no shell) for 400
  (session expired), 403, 404, 405, 429 and 500. 500 rolls back the session.
- Headers on every response: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy:
  strict-origin-when-cross-origin`, `Permissions-Policy` disabling camera,
  microphone and geolocation. In production also HSTS (one year) and secure
  session and remember-me cookies. The timezone cookie is marked `Secure` on
  HTTPS.

## README and CI

- README rewritten in UTF-8: what the app does, stack, local setup, tests,
  deployment and the migration step.
- CI runs on every pull request and on pushes to `main`, on Python 3.11, with
  pip caching and ruff pinned.

## Testing

- CSRF: with protection on, a form post and a JSON post without a token are
  rejected (page and JSON respectively) and succeed with one; every
  `method="POST"` form in the templates carries a token.
- Logout and disconnect: `GET` changes nothing; `POST` works.
- Sign-in limits: lockout after 5 failures, message, success clears,
  per-IP limit, other emails unaffected, unknown emails limited the same way.
- `next` accepted and rejected cases; password length.
- Error pages for each status; 500 handler; headers present; production-only
  headers only in production.

## Out of scope

Email verification and password reset, two-factor sign-in, account deletion
by users, a Content-Security-Policy (the app still has inline scripts).
