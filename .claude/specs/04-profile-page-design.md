# Spec: Profile Page Design

## Overview
This feature replaces the `/profile` placeholder in `app.py` with a real, logged-in-only profile dashboard for Spendly. Beyond basic account details (name, email, member-since date), it summarizes the user's spending: total spent, transaction count, top category, a recent-transactions list, and a per-category breakdown — using the `expenses` table that Step 01 already created but no page has read from until now. This gives users a meaningful landing point right after login/registration, ahead of the expense CRUD steps (Step 7+) that will let them add/edit/delete the expenses this page summarizes. This step also introduces the first route-protection pattern (redirecting anonymous visitors away from `/profile`) and updates the shared navbar in `base.html` to reflect logged-in state.

## Depends on
- Step 01 — Database Setup (`users` table, `expenses` table, `get_db()`) must be complete. It is.
- Step 02 — Registration (creates `users` rows, establishes `session["user_id"]` / `session["user_name"]` convention) must be complete. It is.
- Step 03 — Login and Logout (populates the session this feature reads, provides `/logout`) must be complete. It is.

## Routes
- GET /profile – render the logged-in user's profile dashboard – logged-in only; unauthenticated visitors are redirected to `/login`

No other new routes. The existing `/logout` route (Step 03) is reused by the navbar's sign-out link.

## Database changes
No new tables/columns. This step adds read-only aggregate queries against the existing `expenses` table (Step 01), filtered by `user_id`, alongside the existing `users` lookup:
- `SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM expenses WHERE user_id = ?` — total spent + transaction count
- `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC` — category breakdown (also gives the top category, as the first row)
- `SELECT date, description, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 5` — 5 most recent transactions

All parameterized. No writes.

## Templates
- Create: `templates/profile.html` — extends `base.html`. Structure:
  - Header: avatar circle with initials (`user.initials`, derived from the user's name), name, email, and "Member since" with a calendar icon
  - 3-stat row: total spent, transaction count, top category, each with a Lucide icon
  - "Recent transactions" card: table of up to 5 most recent expenses with a colored category badge per row; empty state ("No expenses logged yet.") when there are none
  - "Category breakdown" card: one row per category with a horizontal percentage bar (`width` inline style, color driven by a `data-category` attribute) and the category total; empty state ("Nothing to break down yet.") when there are none
  - Loads the Lucide icon library via a page-scoped `{% block scripts %}` (CDN script tag + `lucide.createIcons()`) — not added to `base.html`, so no other page pays for it
- Modify: `templates/base.html` — the navbar (`nav-links` block) currently hardcodes "Sign in" / "Get started" for every request. Updated to conditionally show the logged-in user's name (linking to `/profile`) and a "Sign out" link (`/logout`) when `session.user_id` is set, falling back to "Sign in" / "Get started" otherwise. Uses Flask's `session` object directly in Jinja (no context processor needed).

## Files to change
- `app.py`:
  - Two helpers added near the top (after app/DB setup, before routes): `format_member_since(created_at)` (SQLite TEXT timestamp → `"Month YYYY"`, since Jinja has no `strftime` filter) and `get_initials(name)` (derives a 1-2 letter avatar initials string from the user's name)
  - `/profile` route: reads `session.get("user_id")`; redirects to `/login` if absent. Looks up the user; if the row no longer exists (e.g. deleted while the session was still active), clears the session and redirects to `/login` instead of crashing. Otherwise runs the three aggregate queries above and renders `profile.html` with `user`, `stats`, `categories`, and `transactions` context dicts/lists. `password_hash` is never selected, so it can never reach the template.
- `templates/base.html` — conditional navbar markup described above

## Files to create
- `templates/profile.html`

## New dependencies
No new Python packages. One client-side dependency: the Lucide icon library, loaded via CDN, scoped to `profile.html` only.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (no password display or editing in this step — out of scope)
- Use CSS variables – never hardcode hex values (category colors defined as `--cat-<name>` / `--cat-<name>-light` pairs in `:root`, following the existing `--accent`/`--accent-light` pattern)
- All templates extend base.html
- Do not expose `password_hash` to the template context
- Reuse existing CSS classes/patterns where they fit (card look via `.profile-card`/`.profile-stat`, mirroring `.auth-card`/`.mock-stat`) rather than inventing a parallel visual language
- `/profile` must never render for a request with no valid session — always redirect to `/login` in that case
- Handle the zero-expense case cleanly: no division-by-zero when computing category percentages, and explicit empty-state copy instead of a blank table/card

## Definition of done
- [x] Visiting `/profile` while logged out redirects to `/login`
- [x] Logging in (or registering) and then visiting `/profile` shows the correct name, email, and member-since date for that account
- [x] Total spent, transaction count, and top category on `/profile` match the sum/count/grouped-max of that user's rows in `expenses`
- [x] Recent transactions list shows up to 5 most recent expenses with the correct category badge color per category
- [x] Category breakdown bars are colored per category and sized proportional to that category's share of total spend
- [x] A user with zero expenses sees "No expenses logged yet." / "Nothing to break down yet." instead of an empty table/blank card, with no errors
- [x] The navbar shows the logged-in user's name and a "Sign out" link when a session is active, and reverts to "Sign in" / "Get started" after logout
- [x] Signing out (via the navbar) clears the session and returns to the landing page
- [x] No `password_hash` value appears anywhere in the rendered HTML (view source check)
- [x] App starts and `/profile` renders correctly with no errors for a logged-in user, with or without expenses