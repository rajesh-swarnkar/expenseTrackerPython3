# Spec: Login and Logout

## Overview
This feature implements authentication for existing Spendly users. The UI shell for `/login` already exists (`templates/login.html`, fully wired with an `{% if error %}` block), but `app.py` only renders the form on GET — there is no POST handler, no credential check, and no session logic. `/logout` is currently a placeholder that returns plain text. This step wires `/login` up to verify credentials against the `users` table and establish a session, and implements `/logout` to clear that session, letting users move between the registration flow (Step 02) and the profile/expense-tracking steps that depend on a logged-in session.

## Depends on
- Step 01 — Database Setup (`users` table, `get_db()`, `init_db()`, `seed_db()` in `database/db.py`). It is complete.
- Step 02 — Registration (creates the `users` rows this feature authenticates against, and establishes the `session["user_id"]` / `session["user_name"]` convention this feature reuses). It is complete.

## Routes
- GET /login – render the login form (already exists, unchanged) – public
- POST /login – validate email/password against `users`, verify hash, start a session, redirect to a logged-in page – public
- GET /logout – clear the session and redirect to the landing page – logged-in (route itself stays reachable if hit with no session; it simply clears whatever session state exists and redirects)

## Database changes
No database changes. The existing `users` table (id, name, email, password_hash, created_at) already supports login as defined in `database/db.py`.

## Templates
- Create: none
- Modify: none — `templates/login.html` already extends `base.html`, posts to `/login`, and displays validation errors via the existing `{% if error %}` block

## Files to change
- `app.py`:
  - Import `check_password_hash` from `werkzeug.security` alongside the existing `generate_password_hash` import
  - Add POST handling to the `/login` route: read form fields, validate presence, look up the user by email, verify the password hash, set `session["user_id"]` / `session["user_name"]`, redirect to `/profile`; on any failure re-render `login.html` with a generic error (do not reveal whether the email exists)
  - Replace the `/logout` placeholder body with logic that clears the session (`session.clear()`) and redirects to `/` (landing)

## Files to create
None

## New dependencies
No new dependencies. Uses `werkzeug.security.check_password_hash` (mirrors `generate_password_hash`, already used in `database/db.py` and `app.py`) and Flask's built-in `session`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug — verify with `check_password_hash`, never compare plaintext
- Use CSS variables – never hardcode hex values
- All templates extend base.html
- Validate required fields (email, password) server-side even though the form has `required` attributes client-side
- On invalid credentials (unknown email or wrong password), show one generic error message (e.g. "Invalid email or password.") — do not distinguish which field was wrong
- `/logout` must work even if no session exists (no crash on double-logout or logging out while already logged out)

## Definition of done
- [ ] Submitting `/login` with the seeded demo user's credentials (`demo@spendly.com` / `demo123`) establishes a session and redirects away from `/login`
- [ ] Submitting `/login` with a correct email but wrong password re-renders `login.html` with a generic error and does not establish a session
- [ ] Submitting `/login` with an email not in `users` re-renders `login.html` with the same generic error and does not establish a session
- [ ] Submitting `/login` with a missing field re-renders the form with an error instead of crashing
- [ ] Visiting `/logout` after logging in clears the session (subsequent requests no longer show a logged-in state) and redirects to `/`
- [ ] Visiting `/logout` with no active session does not raise an error and still redirects to `/`
- [ ] App starts and `/login` GET still renders correctly with no errors