# Spec: Date Filter for Profile Page

## Overview
This feature adds date-range filtering to the `/profile` dashboard built in Step 04. Today, the profile page's stats (total spent, transaction count, top category), category breakdown, and recent-transactions list are always computed over a user's entire expense history. This step lets a user narrow that view to a time window — a quick preset (this month, last 30 days, etc.) or a custom start/end range — so the dashboard stays useful as expense history grows. It changes only how `/profile` reads and displays existing data; it does not add expense CRUD (that's Step 7+) or any new tables.

## Depends on
- Step 01 — Database Setup (`expenses` table, `get_db()`) must be complete. It is.
- Step 04 — Profile Page Design (`/profile` route, `profile.html`, the three aggregate queries this step adds filtering to) must be complete. It is.

## Routes
- GET /profile – unchanged path, now reads optional query-string filter params and scopes the dashboard to that range – logged-in only (same access rule as Step 04, unaffected by this change)

No new routes. Query params:
- `range` – one of `all` (default), `this_month`, `last_30`, `last_90`, `this_year`
- `start`, `end` – optional custom range (`YYYY-MM-DD`), used instead of `range` when both are present and valid; a preset selected via the UI clears these

## Database changes
No new tables/columns. The three existing read-only queries from Step 04 gain an optional `AND date BETWEEN ? AND ?` clause (added only when a range resolves to concrete start/end bounds; omitted entirely for `all`):
- Total spent + transaction count aggregate
- Category breakdown aggregate
- Recent transactions (still capped at 5 rows, now 5 most recent *within* the active range)

All still parameterized, still no writes.

## Templates
- Create: none
- Modify: `templates/profile.html` — add a filter control above `.profile-stats`: a `GET` form (no page reload via JS needed — plain form submit) with a `<select name="range">` for the presets plus two `<input type="date">` fields (`start`, `end`) for a custom range, submitting to `/profile`. Reflects the currently active filter on reload (selected `<option>`, filled date inputs) and includes a "Clear" link back to plain `/profile`.

## Files to change
- `app.py`:
  - `/profile` route: read `request.args.get("range", "all")` and optional `request.args.get("start")` / `request.args.get("end")`; resolve them to a concrete `(start_date, end_date)` pair or `None` (no filter) using `datetime`; validate custom dates (parse as `YYYY-MM-DD`, ignore/fall back to `all` if malformed or if `start > end`); pass the resolved bounds into the three existing queries and pass the active filter state (`range`, `start`, `end`) into the template context so the UI can reflect it
- `templates/profile.html` — add the filter form described above

## Files to create
None

## New dependencies
No new dependencies. Uses Python's built-in `datetime` for resolving presets to date bounds.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (unaffected by this step — no changes to auth)
- Use CSS variables – never hardcode hex values
- All templates extend base.html
- Filtering is read-only: never mutate `expenses` rows as part of resolving or applying a filter
- Malformed or nonsensical custom ranges (unparseable dates, `start` after `end`) must fall back to the unfiltered (`all`) view rather than raising an error
- Preserve the Step 04 zero-expense behavior: a filter that matches zero expenses shows the existing empty-state copy ("No expenses logged yet." / "Nothing to break down yet."), not a blank or broken card
- Category percentages must be computed relative to the filtered total, not the all-time total, so they still sum to ~100% within the active range

## Definition of done
- [ ] Visiting `/profile` with no query params behaves exactly as before this step (all-time stats, unchanged)
- [ ] Selecting "This month" shows total spent, transaction count, top category, category breakdown, and recent transactions computed only from expenses dated in the current calendar month
- [ ] Selecting "Last 30 days" / "Last 90 days" scopes results to that trailing window
- [ ] Entering a custom start and end date filters all four sections (stats, breakdown, recent transactions) to that inclusive range
- [ ] Submitting a custom range with `start` after `end` falls back to the all-time view instead of crashing
- [ ] Submitting a malformed custom date (e.g. bad format) falls back to the all-time view instead of crashing
- [ ] A range with zero matching expenses shows "No expenses logged yet." / "Nothing to break down yet." with no errors
- [ ] Category breakdown percentages sum to ~100% of the filtered total, not the user's all-time total, when a filter is active
- [ ] After submitting a filter, the select/date inputs reflect the currently active filter on page reload
- [ ] The "Clear" control returns to the unfiltered all-time view
- [ ] App starts and `/profile` renders correctly with no errors, filtered and unfiltered, for a logged-in user with or without expenses