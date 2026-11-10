# Phase 1: Design system and mobile-first shell

Date: 2026-11-10
Status: awaiting review

## Purpose

BrainDump is meant to be a real product that classmates use daily, mostly on
phones. Today it has a generic look, no shared design tokens, and a mobile
experience limited to a slide-out sidebar. Phase 1 gives every page a
consistent identity and a phone-first app shell, without changing any feature
logic.

This is the first of four phases:

1. Design system and mobile-first shell (this spec)
2. Per-page mobile rework (kanban, schedule, flashcards, Pomodoro, forms)
3. Retention features (spaced repetition, richer dashboard, PWA)
4. Reliability and trust (CSRF audit, seeded admin account, rate limiting, README, CI)

## Decisions already made

- Visual direction: "Calm focus". Keep the logo's navy and sky blue, off-white
  paper background, one warm amber accent.
- Stack stays Flask with server-rendered Jinja templates and hand-written CSS.
  No CSS framework, no JS framework.
- Migration strategy: introduce new tokens and keep the existing variable
  names as aliases, so page stylesheets inherit the new look untouched.

## Success criteria

- Every authenticated page and both auth pages render with the new tokens in
  light and dark themes.
- On a 375px-wide viewport, primary navigation is a bottom tab bar; no
  hamburger and no slide-out sidebar.
- No horizontal page scroll at 375px caused by the shell.
- No flash of the wrong theme on page load.
- All shell controls, core buttons and core inputs are at least 44px tall on
  touch devices.
- Text and background token pairs meet WCAG AA (4.5:1 body, 3:1 large text
  and UI components) in both themes.
- Existing pytest suite passes; new shell tests pass.

## Design tokens

Defined in `app/static/css/core/variables.css`. Light values on `:root`, dark
values on `html[data-theme="dark"]`.

### Colour

| Token | Light | Dark | Use |
|---|---|---|---|
| `--color-bg` | `#F7F6F2` | `#0E1626` | Page background |
| `--color-surface` | `#FFFFFF` | `#172236` | Cards, header, nav |
| `--color-surface-2` | `#EFEEE9` | `#1F2D45` | Inset areas, hover |
| `--color-border` | `#E2E0D8` | `#2A3A55` | Dividers, input borders |
| `--color-text` | `#14213D` | `#E8ECF4` | Body text |
| `--color-text-muted` | `#4A5670` | `#A9B4C8` | Secondary text |
| `--color-text-subtle` | `#5F6A85` | `#8492AB` | Hints, placeholders |
| `--color-primary` | `#1D5FD1` | `#6AA5FF` | Actions, links, active nav |
| `--color-primary-hover` | `#174EAD` | `#8BB9FF` | Hover and pressed |
| `--color-on-primary` | `#FFFFFF` | `#0E1626` | Text on primary |
| `--color-accent` | `#F2A33A` | `#F5B556` | Streaks, due markers (fills only) |
| `--color-success` | `#1A7A50` | `#4CC38A` | Success states |
| `--color-warning` | `#9A5B00` | `#F5B556` | Warning states |
| `--color-danger` | `#C73A3A` | `#FF7B7B` | Errors, destructive actions |

Hex values may be adjusted during implementation if a pair fails the contrast
check; the roles and names are fixed.

### Legacy aliases

The existing names map onto the new tokens so page CSS keeps working:

| Legacy name | Maps to |
|---|---|
| `--bg-color-primary` | `--color-bg` |
| `--bg-color-secondary`, `--card-bg` | `--color-surface` |
| `--bg-color-tertiary` | `--color-surface-2` |
| `--text-color-primary`, `--text-color` | `--color-text` |
| `--text-color-secondary` | `--color-text-muted` |
| `--text-color-tertiary`, `--muted-color`, `--text-muted` | `--color-text-subtle` |
| `--border-color` | `--color-border` |
| `--primary-color`, `--accent-color` | `--color-primary` |
| `--box-shadow` | `--shadow-1` |
| `--sidebar-bg`, `--sidebar-text`, `--sidebar-hover` | surface, text, surface-2 |

`--dashboard-gradient` and `--dashboard-shape1..3` are removed along with the
decorative background shapes.

### Type

- Family: Inter variable font, self-hosted as WOFF2 in
  `app/static/fonts/`, `font-display: swap`, with a system-font fallback
  stack. Monospace keeps the system stack.
- Scale: `--text-xs` 12px, `--text-sm` 14px, `--text-base` 16px,
  `--text-lg` 18px, `--text-xl` 22px, `--text-2xl` 28px.
- Inputs use at least 16px so iOS does not zoom on focus.

### Spacing, radius, shadow

- Spacing: `--space-1` to `--space-8` = 4, 8, 12, 16, 24, 32, 48, 64px.
- Radius: `--radius-sm` 6px, `--radius-md` 10px, `--radius-lg` 16px,
  `--radius-full` 999px.
- Shadow: `--shadow-1` (resting cards), `--shadow-2` (sheets, toasts).
- Layout: `--sidebar-width` 240px, `--sidebar-width-collapsed` 64px,
  `--bottom-nav-height` 60px, `--header-height` 56px.

## App shell

### Breakpoints

| Range | Navigation |
|---|---|
| below 768px | Bottom tab bar; sidebar not rendered visibly |
| 768px to 1023px | Sidebar collapsed to icons by default |
| 1024px and up | Sidebar expanded; collapse state remembered in `localStorage` |

### Sidebar (768px and up)

Restyled on `--color-surface` with a right border. The active item gets a
primary-tinted background, primary text and `aria-current="page"`. Active
state is decided server-side from `request.blueprint`, except within the
`main` blueprint where `request.endpoint` separates the dashboard from
settings. The same rule drives the bottom tab bar.

### Bottom tab bar (below 768px)

Fixed to the bottom, `--bottom-nav-height` plus
`env(safe-area-inset-bottom)`. Five tabs, each an icon above a label:

| Tab | Target | Active for blueprints |
|---|---|---|
| Home | dashboard | `main` (dashboard route) |
| Tasks | `tasks.index` | `tasks` |
| Schedule | `calendar.schedule` | `calendar` |
| Study | opens sheet | `pomodoro`, `flashcards` |
| More | opens sheet | `summarizer`, `ai_planner`, `admin`, `main.settings` |

Sheets slide up from the bottom, with a dimmed backdrop:

- Study sheet: Pomodoro, Flashcards.
- More sheet: Summarizer, AI Plan Generator, Settings, Manage Users (admins
  only), theme toggle, Logout.

Sheet behaviour: opened by its tab button (`aria-expanded`,
`aria-controls`); closed by backdrop tap, Escape, or choosing an item; focus
moves into the sheet on open and returns to the tab on close; body scroll is
locked while open. The three direct tabs are ordinary links and work without
JavaScript; the two sheets require JavaScript.

`.main-content` gets bottom padding equal to the tab bar height plus the safe
area so content is never covered. The existing floating Pomodoro widget is
repositioned to sit above the tab bar.

### Header

- Desktop and tablet: sidebar toggle, page title, then avatar with username,
  admin badge, theme toggle and Logout.
- Phone: page title and avatar only. The hamburger, greeting text, Logout and
  theme toggle are hidden; those actions live in the More sheet.
- Avatar: a CSS circle showing the first letter of the username on a primary
  background. The request to `ui-avatars.com` is removed.

### Background

The three `.dashboard-bg-shape` elements and the gradient are removed from
`base.html` and `base.css`. Pages sit on flat `--color-bg`. The invalid
nested rules inside `body { }` in `base.css` are deleted.

## Behaviour changes

### Theme

- Theme is stored on `<html data-theme="light|dark">`. For compatibility with
  page CSS and scripts that target `body.dark-theme`, the class is kept in
  sync on `<body>`.
- A small inline script in `<head>` reads `localStorage.theme`; if unset it
  uses `prefers-color-scheme`. It sets the attribute before first paint.
- `common.js` and `settings.js` share one `setTheme()` function instead of
  each toggling classes separately. The settings page offers Light, Dark and
  System.
- `<meta name="theme-color">` and the web manifest's `theme_color` are
  updated to match the surface colour.

### Flash messages

Rendered as toasts: fixed, top-centre on phones and top-right on larger
screens, coloured by category, each with a close button, auto-dismissed after
6 seconds except errors. Container has `role="status"` and
`aria-live="polite"`.

### Touch and accessibility

- 44px minimum height on `.btn` variants, form controls, nav items and tab
  bar items under `@media (pointer: coarse)`.
- Visible `:focus-visible` ring using `--color-primary` on all interactive
  elements.
- "Skip to content" link as the first focusable element.
- `prefers-reduced-motion: reduce` disables sheet, sidebar and toast
  transitions.

### Auth pages

`login.html` and `register.html` load `variables.css`, the font, and the
theme script, and `login_register.css` is rewritten on the new tokens: a
centred card on the paper background, full-width on phones.

## Files

Modified:

- `app/templates/base.html`
- `app/templates/auth/login.html`, `app/templates/auth/register.html`
- `app/static/css/core/variables.css`, `base.css`, `sidebar.css`,
  `forms.css`, `buttons.css`, `components.css`
- `app/static/css/login_register.css`
- `app/static/js/common.js`, `app/static/js/settings.js`
- `app/templates/settings.html` (System theme option)
- `app/static/favicon/site.webmanifest`

New:

- `app/navigation.py` (navigation state for templates; context processor only)
- `app/templates/components/bottom_nav.html`
- `app/templates/components/theme_init.html` (inline head script)
- `app/static/css/core/bottom-nav.css`
- `app/static/css/core/fonts.css`, `app/static/fonts/Inter-Variable.woff2`
- `tests/test_shell.py`, `tests/test_design_tokens.py`
- `app/__init__.py` is modified only to register the context processor.

No routes, models, services or migrations change.

## Testing

Automated (`tests/test_shell.py`):

- Each main page returns 200 and contains the bottom nav markup.
- The correct nav item carries `aria-current="page"` for one route in each
  blueprint, in both sidebar and bottom nav.
- Manage Users appears in the More sheet for admins only.
- Base template no longer references `ui-avatars.com`.
- Login and register pages link `variables.css`.

Manual, in the browser, for every page at 375px, 768px and 1280px in light
and dark:

- No shell-caused horizontal scroll; content clears the tab bar.
- Sheets open, close, trap and restore focus.
- No theme flash on reload.
- Contrast of token pairs checked with a script against the AA thresholds.

Any page-level layout problems found during the manual pass are recorded as
input for Phase 2, not fixed here.

## Out of scope

- Layout changes to kanban, schedule, flashcards, Pomodoro, summarizer,
  AI planner and admin pages. They inherit colours, type and the shell only.
- Replacing hardcoded hex colours and emoji icons in page-level stylesheets
  and templates.
- New features, PWA service worker, security changes.

## Risks

- Page CSS with hardcoded light colours may look wrong in the new dark theme.
  Mitigation: the manual pass lists these; the worst offenders that make text
  unreadable are fixed in Phase 1, the rest in Phase 2.
- Scripts that check `body.classList.contains('dark-theme')` keep working
  because the class is kept in sync.
