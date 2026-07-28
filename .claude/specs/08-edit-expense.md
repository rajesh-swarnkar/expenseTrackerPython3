# Spec: Edit Expense

## Overview
This feature lets a logged-in user edit an expense they previously logged. The route already exists as a placeholder (`/expenses/<int:id>/edit` returns `"Edit expense — coming in Step 8"`); this step replaces it with a real GET/POST handler that loads the expense, restricts access to its owner, and lets the user update its amount, category, date, and description — reusing the same validation rules and form styling already established by the Add Expense feature.

## Depends on
- Step 01 — Database Setup (`expenses` table, `get_db()`). Complete.
- Step 03 — Login and Logout (`session["user_id"]` convention this feature checks against). Complete.
- Step 04 — Profile Page Design (`profile.html` recent-transactions table, which this feature adds an edit link to). Complete.
- Add Expense (`/expenses/add`, `add_expense.html`) — defines the validation rules and form/CSS pattern this feature reuses. Complete.

## Routes
- GET /expenses/<int:id>/edit – render the edit form pre-filled with the expense's current values – logged-in, owner-only
- POST /expenses/<int:id>/edit – validate and update the expense, redirect to `/profile` – logged-in, owner-only

## Database changes
No database changes. The existing `expenses` table (id, user_id, amount, category, date, description, created_at) already supports editing as defined in `database/db.py`.

## Templates
- Create: `templates/edit_expense.html` — same `auth-section` / `auth-card` / `form-group` structure as `templates/add_expense.html`, pre-populated with the expense's existing amount, category, date, and description; submit button reads "Save changes"
- Modify: `templates/profile.html` — add an "Edit" link/icon to each row of the `txn-table` in the "Recent transactions" card, linking to `url_for('edit_expense', id=txn.id)`

## Files to change
- `app.py`:
  - Replace the `/expenses/<int:id>/edit` placeholder with GET/POST handling:
    - If `session.get("user_id")` is missing, redirect to `login`
    - Look up the expense by id; if it doesn't exist or its `user_id` doesn't match the session user, redirect to `profile` without revealing whether the id exists for another user
    - GET: render `edit_expense.html` with the expense's current values
    - POST: read and validate `amount`, `category`, `date`, `description` using the same rules as `add_expense` (amount > 0, category in `CATEGORIES`, valid `YYYY-MM-DD` date); on error, re-render `edit_expense.html` with the error and the submitted values; on success, run a parameterised `UPDATE expenses SET ... WHERE id = ? AND user_id = ?` and redirect to `profile`
  - `profile()`: add `id` to the `recent` query's selected columns and to the `transactions` list passed to the template, so each row can link to its own edit page

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (not applicable to this feature, no password fields involved)
- Use CSS variables – never hardcode hex values
- All templates extend base.html
- Every lookup and update must be scoped to `WHERE id = ? AND user_id = ?` — a user must never be able to view or modify another user's expense by guessing an id
- Validate all fields server-side using the same rules as Add Expense, even though the form has client-side `required`/`min`/`step` attributes
- Re-render the form with a specific, field-relevant error message on invalid input; never crash on bad input

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an id that doesn't exist redirects to `/profile` without crashing
- [ ] Visiting `/expenses/<id>/edit` for an expense that belongs to a different user redirects to `/profile` and does not display that expense's data
- [ ] GET `/expenses/<id>/edit` for one of the current user's own expenses renders a form pre-filled with its existing amount, category, date, and description
- [ ] Submitting valid changes updates the row in the `expenses` table and redirects to `/profile`, where the updated values are visible in "Recent transactions"
- [ ] Submitting an amount that is zero, negative, or non-numeric re-renders the form with an error and leaves the database unchanged
- [ ] Submitting a category not in `CATEGORIES` re-renders the form with an error and leaves the database unchanged
- [ ] Submitting an invalid or missing date re-renders the form with an error and leaves the database unchanged
- [ ] The "Recent transactions" table on `/profile` shows a working edit link on each row that opens the correct expense's edit page
- [ ] App starts and all existing routes (`/login`, `/profile`, `/expenses/add`) continue to work with no errors