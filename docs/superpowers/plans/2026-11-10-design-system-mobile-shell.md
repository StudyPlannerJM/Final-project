# Design System and Mobile-First Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every BrainDump page one set of design tokens ("Calm focus") and a phone-first app shell with a bottom tab bar, without changing feature logic.

**Architecture:** New tokens live in `core/variables.css`; the existing variable names become aliases so the 30+ page stylesheets inherit the new look untouched. Navigation state is computed by one pure Python function exposed to templates through a context processor, and drives both the sidebar and the new bottom tab bar. Theme is set on `<html data-theme>` by an inline head script before first paint.

**Tech Stack:** Flask 3, Jinja2, hand-written CSS, vanilla JS, pytest. Python 3.14 in `.venv`.

**Spec:** `docs/superpowers/specs/2026-11-10-design-system-mobile-shell-design.md` — read it first; token tables and behaviour rules are not repeated here.

## Global Constraints

- No CSS or JS framework; no new Python dependencies.
- No changes to routes, models, services or migrations. One new module, `app/navigation.py`, is allowed (context processor only).
- Do not touch or commit the pre-existing uncommitted changes in `app/config.py`, `app/models.py`, `requirements.txt`, `run.py`. Stage files by explicit path, never `git add -A`.
- Work on branch `phase-1-design-system`. Do not push.
- Breakpoints: phone below 768px, tablet 768–1023px, desktop 1024px and up.
- Token names and roles are exactly those in the spec's colour, type, spacing, radius and layout tables. Hex values may change only to pass contrast.
- Contrast: 4.5:1 for text pairs, 3:1 for UI components, both themes.
- Touch targets: 44px minimum under `@media (pointer: coarse)`.
- Inputs: font-size at least 16px.
- Keep `body.dark-theme` in sync with `html[data-theme="dark"]`; page CSS and scripts depend on it.
- Run tests with `.venv/bin/python -m pytest <path> -q --no-cov`. Full suite baseline: 256 passed.
- Commit after each task; end each message with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.

## Review Focus

1. **Storage blocked** (Safari private mode, cookies disabled): `localStorage` access throws. The page must still render in the system theme and the toggle must still work for that page view. Pinned in Task 2.
2. **Pages outside any blueprint** (404, or `request.endpoint` is `None`): navigation must render with no active item rather than raise. Pinned in Task 3.
3. **Long or unusual usernames** (30 characters, non-Latin, leading emoji or space): header must not overflow at 375px and the avatar must show one visible character or a fallback. Pinned in Task 3 (initial) and Task 7 (overflow).
4. **Several flash messages at once, or one very long message**: toasts stack, stay on screen, wrap, and each closes independently. Pinned in Task 5 and Task 7.
5. **Narrow and short viewports** (320px wide; phone in landscape, about 360px tall): five tabs fit without clipping labels, and an open sheet scrolls internally rather than extending off screen. Pinned in Task 7.

---

## File Structure

| File | Responsibility |
|---|---|
| `app/navigation.py` (new) | `nav_state()` pure function, `user_initial()`, context processor |
| `app/templates/components/theme_init.html` (new) | Inline head script that sets theme before paint |
| `app/templates/components/bottom_nav.html` (new) | Tab bar plus Study and More sheets |
| `app/static/css/core/fonts.css` (new) | `@font-face` for Inter |
| `app/static/css/core/bottom-nav.css` (new) | Tab bar and sheet styles |
| `app/static/css/core/variables.css` | Tokens and legacy aliases only |
| `app/static/css/core/base.css` | Reset, body, layout, header, skip link, focus ring, reduced motion |
| `app/static/css/core/sidebar.css` | Sidebar at tablet and desktop |
| `app/static/css/core/components.css` | Toasts, floating timer, shared components |
| `app/static/js/common.js` | `window.BrainDump.setTheme`, sidebar, sheets, toasts |
| `tests/test_design_tokens.py` (new) | Token presence and contrast |
| `tests/test_shell.py` (new) | Nav state, shell markup, auth pages |

---

### Task 1: Tokens, aliases and font

**Files:**
- Modify: `app/static/css/core/variables.css` (full rewrite)
- Create: `app/static/css/core/fonts.css`, `app/static/fonts/Inter-Variable.woff2`
- Test: `tests/test_design_tokens.py`

**Interfaces:**
- Produces: every `--color-*`, `--text-*`, `--space-*`, `--radius-*`, `--shadow-*` and layout token named in the spec, on `:root` (light) and `html[data-theme="dark"]` (dark colours only); every legacy alias in the spec's alias table, defined once on `:root` as `var(--color-…)` so it follows the theme automatically.

- [ ] **Step 1: Write the failing tests**

`tests/test_design_tokens.py` reads `variables.css` as text; no Flask app needed. Helpers: `parse_block(css, selector) -> dict[str, str]` and `contrast(hex_a, hex_b) -> float` (WCAG relative luminance formula).

```python
TEXT_PAIRS = [  # (foreground, background) must be >= 4.5
    ("--color-text", "--color-bg"), ("--color-text", "--color-surface"),
    ("--color-text", "--color-surface-2"),
    ("--color-text-muted", "--color-bg"), ("--color-text-muted", "--color-surface"),
    ("--color-text-subtle", "--color-bg"), ("--color-text-subtle", "--color-surface"),
    ("--color-primary", "--color-surface"), ("--color-primary", "--color-bg"),
    ("--color-on-primary", "--color-primary"),
    ("--color-success", "--color-surface"), ("--color-warning", "--color-surface"),
    ("--color-danger", "--color-surface"),
]
LEGACY = ["--bg-color-primary", "--bg-color-secondary", "--bg-color-tertiary",
          "--card-bg", "--text-color-primary", "--text-color", "--text-color-secondary",
          "--text-color-tertiary", "--muted-color", "--text-muted", "--border-color",
          "--primary-color", "--accent-color", "--box-shadow",
          "--sidebar-bg", "--sidebar-text", "--sidebar-hover"]

@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("fg,bg", TEXT_PAIRS)
def test_text_contrast_meets_aa(theme, fg, bg): ...   # assert contrast >= 4.5

@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_on_accent_fill_is_readable(theme): ...
    # light: contrast(light --color-text, --color-accent) >= 4.5
    # dark:  contrast(dark --color-bg,   --color-accent) >= 4.5  (dark text on amber)

@pytest.mark.parametrize("name", LEGACY)
def test_legacy_alias_points_at_new_token(name): ...   # value starts with "var(--"

def test_removed_tokens_are_gone(): ...   # no "--dashboard-gradient", no "--dashboard-shape"

def test_dark_block_defines_every_colour_token(): ...   # same --color-* key set as :root
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_design_tokens.py -q --no-cov`
Expected: FAIL (tokens not defined).

- [ ] **Step 3: Rewrite `variables.css`**

Start from the spec's tables. Adjust any hex that fails a pair, keeping hue and role, and update the spec table to match in the same commit.

- [ ] **Step 4: Add the font**

Download `InterVariable.woff2` from the official Inter release (github.com/rsms/inter, SIL Open Font License) to `app/static/fonts/Inter-Variable.woff2`. **This is a file download: confirm with the user before fetching.** If declined, skip the file and `fonts.css`, and set `--font-sans` to the system stack only.

`fonts.css`: one `@font-face`, family `Inter`, weight range `100 900`, `font-display: swap`. In `variables.css`: `--font-sans: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;` and `--font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;`.

- [ ] **Step 5: Run tests, then commit**

Run: `.venv/bin/python -m pytest tests/test_design_tokens.py -q --no-cov` — expected PASS.

```bash
git add app/static/css/core/variables.css app/static/css/core/fonts.css app/static/fonts tests/test_design_tokens.py docs/superpowers/specs
git commit -m "feat(design): add design tokens, legacy aliases and Inter font"
```

---

### Task 2: Theme without flash

**Files:**
- Create: `app/templates/components/theme_init.html`
- Modify: `app/templates/components/favicons.html`, `app/static/favicon/site.webmanifest`, `app/static/js/common.js` (theme block, lines 9–18), `app/static/js/settings.js` (lines 23–38), `app/templates/settings.html` (theme `<select>`, line 27)
- Test: `tests/test_shell.py`

**Interfaces:**
- Produces: `components/theme_init.html`, includable in any `<head>`. Global `window.BrainDump = { getThemePreference(): 'light'|'dark'|'system', setTheme(pref: 'light'|'dark'|'system'): void }`, defined by the inline script so it exists before `common.js` loads. `setTheme` resolves `system` through `matchMedia('(prefers-color-scheme: dark)')`, sets `document.documentElement.dataset.theme`, toggles `dark-theme` on `<body>` when body exists, updates `<meta name="theme-color">` (`#FFFFFF` light, `#172236` dark), and stores the preference under `localStorage.theme`.

- [ ] **Step 1: Write the failing tests**

```python
def test_theme_script_is_inline_in_head_before_stylesheets(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    head = html.split('</head>')[0]
    assert 'data-theme' in head and 'prefers-color-scheme' in head
    assert head.index('BrainDump') < head.index('variables.css')

def test_theme_script_guards_storage_access(auth_client):
    head = auth_client.get('/').get_data(as_text=True).split('</head>')[0]
    assert 'try' in head and 'catch' in head     # Review Focus 1

def test_settings_offers_system_theme(auth_client):
    html = auth_client.get('/settings').get_data(as_text=True)
    for value in ('light', 'dark', 'system'):
        assert f'value="{value}"' in html
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_shell.py -q --no-cov` — expected FAIL.

- [ ] **Step 3: Implement**

- `theme_init.html`: one `<script>` defining `window.BrainDump` as above. Every `localStorage` read and write is inside `try/catch`; on failure the preference is `system` and is held in a variable for the page's lifetime. Because `<body>` does not exist yet, also register a `DOMContentLoaded` handler that syncs the `dark-theme` body class. Listen for `change` on the media query and re-apply when the preference is `system`.
- Include it in `base.html` immediately after the viewport meta, before any stylesheet link (Task 3 rewrites the rest of `base.html`; here add only the include and the `fonts.css` link).
- `common.js`: the header toggle calls `BrainDump.setTheme(current resolved theme === 'dark' ? 'light' : 'dark')`. Delete the old class and storage logic.
- `settings.js`: select value comes from `getThemePreference()`; `change` calls `setTheme(value)`. `settings.html`: add `<option value="system">System</option>`.
- `favicons.html` and `site.webmanifest`: `theme-color` `#FFFFFF`; manifest `background_color` `#F7F6F2`.

- [ ] **Step 4: Run tests, then commit**

Run: `.venv/bin/python -m pytest tests/test_shell.py -q --no-cov` — expected PASS.

```bash
git add app/templates/components/theme_init.html app/templates/components/favicons.html app/templates/base.html app/templates/settings.html app/static/favicon/site.webmanifest app/static/js/common.js app/static/js/settings.js tests/test_shell.py
git commit -m "feat(theme): apply theme before paint and add system option"
```

---

### Task 3: Navigation state and shell markup

**Files:**
- Create: `app/navigation.py`, `app/templates/components/bottom_nav.html`
- Modify: `app/__init__.py` (register context processor after blueprints), `app/templates/base.html` (full rewrite of `<body>`)
- Test: `tests/test_shell.py`

**Interfaces:**
- Produces, in `app/navigation.py`:
  - `nav_state(blueprint: str | None, endpoint: str | None) -> dict[str, str | None]` returning `{"item": …, "tab": …}`.

    | blueprint / endpoint | item | tab |
    |---|---|---|
    | `main` with endpoint `main.settings` | `settings` | `more` |
    | `main` otherwise | `dashboard` | `home` |
    | `tasks` | `tasks` | `tasks` |
    | `calendar` | `schedule` | `schedule` |
    | `pomodoro` | `pomodoro` | `study` |
    | `flashcards` | `flashcards` | `study` |
    | `summarizer` | `summarizer` | `more` |
    | `ai_planner` | `ai_planner` | `more` |
    | `admin` | `admin` | `more` |
    | anything else, including `None` | `None` | `None` |

  - `user_initial(username: str | None) -> str`: first non-whitespace character, upper-cased; `"?"` if none.
  - `register_navigation(app: Flask) -> None`: context processor injecting `nav` (the dict for the current request) and `user_initial` (the function).
- Produces, in markup (Tasks 4 and 5 style these; names are fixed):
  - `<a class="skip-link" href="#main-content">`, `<main id="main-content" class="main-content">`
  - Sidebar links: `.nav-link`, plus `.is-active` and `aria-current="page"` when `nav.item` matches.
  - Header: `.top-header`, `.header-left`, `.header-right`, `.user-chip` containing `.avatar` (text is `user_initial(current_user.username)`), `.user-name`, `.admin-badge`; `#theme-toggle`; `.logout-btn`.
  - Bottom nav: `<nav class="bottom-nav" aria-label="Primary">` with five `.bottom-nav__item` children carrying `data-tab="home|tasks|schedule|study|more"`. Home, Tasks, Schedule are `<a>`; Study and More are `<button type="button" aria-expanded="false" aria-controls="sheet-study|sheet-more">`. Active tab gets `.is-active`; active `<a>` also gets `aria-current="page"`.
  - Sheets: `<div class="sheet" id="sheet-study|sheet-more" role="dialog" aria-modal="true" aria-labelledby="…" hidden>` containing `.sheet__title` and `.sheet__link` items (active one `.is-active` + `aria-current="page"`). More sheet also holds `<button class="sheet__link" data-action="toggle-theme">` and the Logout link. One shared `<div class="sheet-backdrop" hidden>`.
  - Toast container: `<div class="toasts" role="status" aria-live="polite">` with `.toast.toast--{category}` children, each containing `.toast__text` and `<button class="toast__close" aria-label="Dismiss">`.
- Removed from `base.html`: the three `.dashboard-bg-shape` divs, the `ui-avatars.com` image, `.sidebar-overlay`.

- [ ] **Step 1: Write the failing tests**

```python
from app.navigation import nav_state, user_initial

@pytest.mark.parametrize("bp,ep,item,tab", [
    ("main", "main.dashboard", "dashboard", "home"),
    ("main", "main.settings", "settings", "more"),
    ("tasks", "tasks.index", "tasks", "tasks"),
    ("calendar", "calendar.schedule", "schedule", "schedule"),
    ("pomodoro", "pomodoro.index", "pomodoro", "study"),
    ("flashcards", "flashcards.index", "flashcards", "study"),
    ("summarizer", "summarizer.index", "summarizer", "more"),
    ("ai_planner", "ai_planner.generator", "ai_planner", "more"),
    ("admin", "admin.manage_users", "admin", "more"),
    (None, None, None, None),                # Review Focus 2
    ("auth", "auth.login", None, None),
])
def test_nav_state(bp, ep, item, tab):
    assert nav_state(bp, ep) == {"item": item, "tab": tab}

@pytest.mark.parametrize("name,expected", [
    ("marcos", "M"), ("  ana", "A"), ("élodie", "É"), ("日本", "日"),
    ("", "?"), ("   ", "?"), (None, "?"),      # Review Focus 3
])
def test_user_initial(name, expected):
    assert user_initial(name) == expected

PAGES = [("/", "home"), ("/tasks", "tasks"), ("/pomodoro", "study"),
         ("/flashcards", "study"), ("/summarizer", "more"), ("/settings", "more")]

@pytest.mark.parametrize("url,tab", PAGES)
def test_page_renders_bottom_nav_with_active_tab(auth_client, url, tab):
    html = auth_client.get(url, follow_redirects=True).get_data(as_text=True)
    assert 'class="bottom-nav"' in html
    assert re.search(rf'bottom-nav__item[^"]*is-active[^>]*data-tab="{tab}"'
                     rf'|data-tab="{tab}"[^>]*is-active', html)

def test_exactly_one_sidebar_item_is_current(auth_client):
    html = auth_client.get('/tasks').get_data(as_text=True)
    sidebar = html.split('class="sidebar"')[1].split('</nav>')[0]
    assert sidebar.count('aria-current="page"') == 1

def test_404_page_renders_without_active_nav(auth_client):
    assert auth_client.get('/no-such-page').status_code == 404   # must not be 500

def test_manage_users_only_for_admins(auth_client, db_session, test_user):
    assert 'Manage Users' not in auth_client.get('/').get_data(as_text=True)
    test_user.is_admin = True; db_session.session.commit()
    assert 'Manage Users' in auth_client.get('/').get_data(as_text=True)

def test_shell_has_no_third_party_avatar_or_bg_shapes(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    assert 'ui-avatars.com' not in html and 'dashboard-bg-shape' not in html

def test_flash_renders_as_toast(auth_client):
    with auth_client.session_transaction() as sess:
        sess['_flashes'] = [('success', 'Saved'), ('danger', 'Broken')]
    html = auth_client.get('/').get_data(as_text=True)
    assert 'class="toast toast--success"' in html
    assert 'class="toast toast--danger"' in html
    assert html.count('toast__close') == 2
```

Confirm the real URLs for `PAGES` from each blueprint's `url_prefix` and route decorators before running.

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_shell.py -q --no-cov` — expected FAIL (`app.navigation` missing).

- [ ] **Step 3: Implement `app/navigation.py` and register it in `create_app`**

- [ ] **Step 4: Rewrite `base.html` body and create `bottom_nav.html`**

Use the markup names in Interfaces. Keep the existing blocks (`title`, `head_extra`, `page_title`, `content`, `body_extra`) and the existing nav order and labels; shorten the bottom-sheet label "AI Plan Generator" only if it wraps at 320px. Add `core/bottom-nav.css` to the stylesheet links. Update Font Awesome to the current 6.x release on the same CDN. `base.html` is also rendered for unauthenticated error pages: wrap every `current_user.username` use in `{% if current_user.is_authenticated %}`.

- [ ] **Step 5: Run tests and the full suite, then commit**

Run: `.venv/bin/python -m pytest -q --no-cov` — expected: all pass, count ≥ 256 plus new tests. Existing tests that assert old markup (`flash-message`, greeting text) are updated to the new names, not deleted.

```bash
git add app/navigation.py app/__init__.py app/templates/base.html app/templates/components/bottom_nav.html tests
git commit -m "feat(shell): add nav state, bottom tab bar markup and local avatar"
```

---

### Task 4: Shell layout, sidebar, tab bar and sheets

**Files:**
- Modify: `app/static/css/core/base.css` (full rewrite), `app/static/css/core/sidebar.css` (full rewrite), `app/static/js/common.js` (sidebar block, lines 20–64)
- Create: `app/static/css/core/bottom-nav.css`
- Modify: `app/static/css/core/components.css:133-200` (`#floating-pomodoro` position)

**Interfaces:**
- Consumes: markup names from Task 3; tokens from Task 1; `BrainDump.setTheme` from Task 2.
- Produces: JS functions inside `common.js`, not global: `openSheet(id: string, trigger: HTMLElement): void`, `closeSheet(): void`. `localStorage.sidebarCollapsed` holds `'1'` or `'0'` (desktop only, wrapped in `try/catch`).

There is no JS test runner in this project; this task is verified in the browser. Start the app with the `run` skill or `.venv/bin/python run.py` (port 5001) and log in with a user created through the register page.

- [ ] **Step 1: `base.css`**

Body on `--color-bg`, `--font-sans`, `--text-base`. Delete the nested rules inside `body {}` and all `.dashboard-bg-shape` rules. `.wrapper` flex; `.main-content` padding `--space-5` (phone `--space-4`), and below 768px `padding-bottom: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom) + var(--space-4))`. Header: height `--header-height`, surface background, bottom border, sticky top, with `padding-top: env(safe-area-inset-top)`. Below 768px hide `#sidebar-toggle`, `.user-name`, `.admin-badge`, `.logout-btn`, `#theme-toggle`. `.avatar`: 32px circle, `--color-primary` background, `--color-on-primary` text. `.user-name`: `max-width: 16ch`, ellipsis. Page title: single line, ellipsis. Also: `.skip-link` (visually hidden until focused), global `:focus-visible` ring `2px solid var(--color-primary)` with 2px offset, and a `prefers-reduced-motion: reduce` block setting transition and animation durations to near zero.

- [ ] **Step 2: `sidebar.css`**

`display: none` below 768px. Surface background, right border, width `--sidebar-width`; `.collapsed` width `--sidebar-width-collapsed`. 768–1023px: collapsed by default regardless of stored state. `.nav-link.is-active`: background `color-mix(in srgb, var(--color-primary) 12%, transparent)`, text `--color-primary`, weight 600. Sticky, full viewport height, own vertical scroll.

- [ ] **Step 3: `bottom-nav.css`**

`.bottom-nav`: `display: none` at 768px and up; otherwise fixed bottom, five equal columns, height `--bottom-nav-height`, `padding-bottom: env(safe-area-inset-bottom)`, surface background, top border, `z-index: 1000`. Items: icon above `--text-xs` label, min 44px, colour `--color-text-muted`, active `--color-primary`. `.sheet`: fixed, bottom `0`, full width, `max-height: 80dvh`, `overflow-y: auto`, top corners `--radius-lg`, `--shadow-2`, `z-index: 1200`, slides up with `transform`. `.sheet__link`: 52px rows, icon plus label. `.sheet-backdrop`: fixed inset, `rgba(0,0,0,.45)`, `z-index: 1100`.

- [ ] **Step 4: `common.js` sidebar and sheets**

Sidebar: toggle button collapses on desktop and persists the state; restore on load at 1024px and up. Remove the mobile slide-out code and overlay handling. Sheets: clicking a `.bottom-nav__item[aria-controls]` calls `openSheet`; opening sets `hidden = false` on sheet and backdrop, `aria-expanded="true"` on the trigger, adds `sheet-open` to `<body>` (CSS: `overflow: hidden`), and focuses the first `.sheet__link`. `closeSheet` reverses this and returns focus to the trigger. Close on backdrop click, Escape, and any `.sheet__link` click. Tab and Shift+Tab cycle within the open sheet. Opening one sheet while another is open closes the first. Crossing to 768px or wider closes any open sheet. `[data-action="toggle-theme"]` flips the theme and leaves the sheet open.

- [ ] **Step 5: Floating Pomodoro widget**

Below 768px set `#floating-pomodoro { bottom: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom) + var(--space-3)); }` and `z-index` below the sheet backdrop.

- [ ] **Step 6: Verify in the browser**

At 375×812, 768×1024 and 1280×800, on Dashboard and Tasks:
- 375: tab bar visible, sidebar and hamburger absent, last content element fully visible above the bar, `document.documentElement.scrollWidth <= window.innerWidth`.
- Study and More sheets open, close by backdrop, Escape and link; focus returns to the tab.
- 768: icon-only sidebar, no tab bar. 1280: full sidebar; collapse survives reload.
- Console has no errors.

- [ ] **Step 7: Run the full suite, then commit**

```bash
git add app/static/css/core/base.css app/static/css/core/sidebar.css app/static/css/core/bottom-nav.css app/static/css/core/components.css app/static/js/common.js
git commit -m "feat(shell): responsive layout with bottom tab bar and sheets"
```

---

### Task 5: Core components — buttons, forms, toasts

**Files:**
- Modify: `app/static/css/core/buttons.css`, `app/static/css/core/forms.css`, `app/static/css/core/components.css`, `app/static/js/common.js`

**Interfaces:**
- Consumes: toast markup from Task 3, tokens from Task 1.
- Produces: no new names. Existing class names in these three files are preserved; only declarations change.

- [ ] **Step 1: Buttons and forms**

Replace every hardcoded colour, radius, shadow and font size in `buttons.css` and `forms.css` with tokens. Inputs, selects and textareas: `font-size: max(16px, var(--text-base))`, `--radius-md`, border `--color-border`, focus border `--color-primary`. Under `@media (pointer: coarse)`: `min-height: 44px` on buttons and form controls. Do not rename or remove any selector: run `grep -o '^\.[a-zA-Z0-9_-]*' <file> | sort -u` before and after and confirm the lists match.

- [ ] **Step 2: Toasts**

In `components.css` replace the `.flash-messages` / `.flash-message` rules (lines 65–120) with `.toasts` (fixed; top-centre below 768px, top-right otherwise; column, gap `--space-2`; `z-index: 1300`; `max-height: 60dvh; overflow-y: auto`; offset by `env(safe-area-inset-top)`) and `.toast` (surface, `--shadow-2`, `--radius-md`, 4px left border coloured by `--color-success|danger|warning|primary` for `success|danger|warning|info`, `max-width: min(92vw, 420px)`, text wraps with `overflow-wrap: anywhere`). Categories used by the app: confirm with `grep -rhoE "flash\([^)]*'(\w+)'\)" app/routes | sort | uniq -c` and style each one found; unknown categories fall back to the `info` style.

In `common.js`: `.toast__close` removes its toast; toasts other than `toast--danger` and `toast--error` auto-remove after 6000ms; hovering or focusing a toast pauses its timer.

- [ ] **Step 3: Remaining `components.css` rules**

Tokenise the rest of the file, including `#floating-pomodoro` (replace `'Inter', sans-serif` and `'Courier New'` with `--font-sans` and `--font-mono`). Delete `.dark-theme` overrides that only restated colours now handled by tokens.

- [ ] **Step 4: Verify in the browser**

Trigger a success flash (add a task) and an error flash (submit an invalid form). Confirm: toast appears without shifting content, success disappears after about 6s, error stays, close button works, both themes readable. Temporarily flash three messages plus one 300-character message from a route to check stacking and wrapping at 375px (Review Focus 4), then revert that edit.

- [ ] **Step 5: Run the full suite, then commit**

```bash
git add app/static/css/core/buttons.css app/static/css/core/forms.css app/static/css/core/components.css app/static/js/common.js
git commit -m "feat(design): tokenise core components and turn flashes into toasts"
```

---

### Task 6: Login and register pages

**Files:**
- Modify: `app/templates/auth/login.html`, `app/templates/auth/register.html`, `app/static/css/login_register.css` (full rewrite)
- Test: `tests/test_shell.py`

**Interfaces:**
- Consumes: `components/theme_init.html`, `core/variables.css`, `core/fonts.css`, `core/forms.css`, `core/buttons.css`.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("url", ["/auth/login", "/auth/register"])
def test_auth_pages_use_design_system(client, url):
    head = client.get(url).get_data(as_text=True).split('</head>')[0]
    assert 'core/variables.css' in head and 'data-theme' in head
    assert head.index('BrainDump') < head.index('variables.css')
```

- [ ] **Step 2: Run to verify failure**, then implement

Both templates: include `theme_init.html` first, then link `variables.css`, `fonts.css`, `base.css`, `forms.css`, `buttons.css`, `login_register.css`. Keep form fields, names, ids and the flash list exactly as they are (existing auth tests depend on them). `login_register.css`: body centred on `--color-bg`; `.container` is a surface card, `max-width: 400px`, `--radius-lg`, `--shadow-1`, padding `--space-6`; below 480px the card fills the width with no shadow and `--space-4` padding. In dark theme the logo PNG has a light background: put it on a `--radius-md` white tile so it does not look like a pasted rectangle.

- [ ] **Step 3: Run tests, check both pages at 375px and 1280px in both themes, then commit**

```bash
git add app/templates/auth app/static/css/login_register.css tests/test_shell.py
git commit -m "feat(auth): restyle login and register on the design system"
```

---

### Task 7: Full-page pass and Phase 2 findings

**Files:**
- Create: `docs/superpowers/specs/phase-2-findings.md`
- Modify: page-level CSS only where a rule below requires it

No new automated tests; this task is the spec's manual verification.

- [ ] **Step 1: Seed realistic data**

Through the UI, create one user with a 30-character username, three tasks across statuses, one deck with three cards, and one completed Pomodoro, so pages are not empty.

- [ ] **Step 2: Walk every page**

Pages: dashboard, tasks (list and kanban), add task, edit task, schedule, Pomodoro, Pomodoro sessions, decks, add/edit deck, flashcards study, add/edit flashcards, summarizer list, upload, view summary, AI plan generator, my study plans, view study plan, settings, manage users, user form, calendar sync prompt, login, register.

Viewports: 320×568, 375×812, 640×360 (landscape phone), 768×1024, 1280×800. Themes: light and dark.

For each page record: horizontal scroll (`scrollWidth > innerWidth`), text contrast failures, content hidden under the tab bar or header, controls under 44px on the phone sizes, console errors.

- [ ] **Step 3: Fix now, in Phase 1, only these classes of problem**

- Text unreadable in either theme (contrast below 3:1) because of a hardcoded colour: replace that colour with the matching token.
- Horizontal page scroll caused by the shell (header, tab bar, sheets, toasts).
- Header overflow with the 30-character username at 375px (Review Focus 3).
- Tab labels clipped at 320px, or a sheet taller than the viewport at 640×360 that does not scroll (Review Focus 5).
- Any page-level rule that positions something `fixed` at the bottom and now collides with the tab bar.

- [ ] **Step 4: Record everything else**

`phase-2-findings.md`: one section per page, each finding as "viewport / theme — what is wrong — file and selector". Include remaining hardcoded-colour counts per stylesheet (`grep -c -E '#[0-9a-fA-F]{3,6}\b'`) and every emoji used as an icon.

- [ ] **Step 5: Final checks**

Run: `.venv/bin/python -m pytest -q --no-cov` — expected: all pass.
Run: `.venv/bin/ruff check app tests` — expected: no new findings compared with `main`.
Reload any page in dark theme with the network throttled to "Slow 4G": no light flash.
Confirm `git status --short` shows only the four pre-existing modified files.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/phase-2-findings.md app/static/css
git commit -m "fix(design): readability fixes from full-page pass; record Phase 2 findings"
```
