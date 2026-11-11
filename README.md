# BrainDump

A study planner for students, built with Flask. It brings tasks, a calendar, a
Pomodoro timer, flashcards with spaced repetition, a document summarizer and
an AI study-plan generator into one app that works well on a phone and can be
installed to the home screen.

## Features

- **Dashboard**: what to do today (tasks due, flashcards due), a study streak,
  study time for the last 7 days and progress per flashcard deck.
- **Tasks**: a board with To-Do, Doing and Done columns. Drag and drop on a
  computer; on a phone, swipe between columns and use "Move to". Overdue
  tasks are flagged.
- **Schedule**: agenda, week, month and day views, with optional two-way sync
  to Google Calendar.
- **Pomodoro timer**: 25/45/60-minute or custom sessions, a floating timer
  while you use other pages, and session history.
- **Flashcards**: decks, and a review session that brings each card back just
  before you are likely to forget it (spaced repetition, Again / Hard / Good /
  Easy).
- **Summarizer**: upload a document and get a summary.
- **AI study plans**: a week-by-week plan from a subject, the time available
  and your level (Google Gemini). Plans can be turned into tasks and
  flashcards.
- **Installable app**: add it to the home screen; opening it offline shows a
  friendly page instead of a browser error.
- Light and dark themes (or follow the device), keyboard and screen-reader
  friendly controls.

## Tech stack

Python 3.11, Flask 3, SQLAlchemy with Alembic migrations (Flask-Migrate),
Flask-Login, Flask-WTF. Server-rendered Jinja templates with hand-written CSS
(design tokens in `app/static/css/core/variables.css`) and plain JavaScript.
SQLite for local development, PostgreSQL in production. Tests with pytest;
linting with ruff.

## Run it locally

```bash
git clone https://github.com/StudyPlannerJM/Final-project.git
cd Final-project
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

Edit `.env` and set at least `SECRET_KEY` to a long random string. The other
keys are only needed for the features that use them:

| Variable | Needed for |
|---|---|
| `SECRET_KEY` | Always (sessions and CSRF tokens) |
| `DATABASE_URL` | Optional locally; defaults to SQLite in `instance/` |
| `GEMINI_API_KEY` | AI study plans ([get a key](https://aistudio.google.com/apikey)) |
| `APYHUB_API_KEY` | Document summarizer ([apyhub.com](https://apyhub.com/)) |
| `client_secret.json` (a file, not a variable) | Google Calendar sync; see below |

Then create the database and start the app:

```bash
flask db upgrade
python run.py
```

Open http://localhost:5000 (or the port in `PORT`).

In development, `run.py` creates demo accounts so you can sign in straight
away: `student1@study.com` / `user123` and an admin account
`admin@admin.com` / `admin`. They are never created when `FLASK_ENV` is
`production`. Set `SEED_DEFAULT_USERS=false` to turn them off locally.

After pulling changes that include new migrations, run `flask db upgrade`
again. Existing data is kept.

### Google Calendar (optional)

1. In the [Google Cloud console](https://console.cloud.google.com/), create a
   project and enable the Google Calendar API.
2. Create OAuth 2.0 credentials (web application) with the redirect URI
   `<address you open the app on>/calendar/oauth2callback`, for example
   `http://localhost:5000/calendar/oauth2callback`.
3. Download the credentials as JSON, name the file `client_secret.json` and put
   it in the project folder (the folder you run the app from). It is listed in
   `.gitignore`; never commit it.

## Tests and linting

```bash
pytest            # runs the suite with a coverage report
ruff check .
```

The tests use an in-memory SQLite database and need no API keys. CI runs both
on every pull request (`.github/workflows/python-app.yml`).

## Deploying

The app is deployed on Render (`render.yaml`). Production needs
`FLASK_ENV=production`, a `SECRET_KEY` and a PostgreSQL `DATABASE_URL`.
Run `flask db upgrade` on each deploy that includes migrations.

In production the app sends secure cookies and HSTS, and trusts one proxy hop
for the client address (Render's load balancer). If the platform puts more
proxies in front of the app, set `PROXY_FIX_X_FOR` to that number; blocked
sign-ins are logged with the address seen and the `X-Forwarded-For` header, so
this can be checked after deploying.

## Security

- CSRF protection on every form and every script request.
- Failed sign-ins are limited within 15 minutes: 5 per email from one network
  address, 20 per email in total, and 50 per network address. Someone guessing
  a classmate's password blocks only their own address. Passwords need at
  least 8 characters.
- Security headers on every response (no MIME sniffing, no framing by other
  sites, strict referrer policy).

## Project layout

```
app/
  routes/       one blueprint per area (tasks, calendar, flashcards, ...)
  services/     business logic and queries
  templates/    Jinja templates; components/ holds shared pieces
  static/       css/ (core/ = design system), js/, fonts/, favicon/
  models.py     SQLAlchemy models
migrations/     Alembic migrations
tests/          pytest suite
docs/superpowers/  design specs and implementation plans
```
