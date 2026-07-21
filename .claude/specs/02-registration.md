# Spec: Registration

## Overview
This feature implements user registration for Spendly. The landing page and UI shell for `/register` already exist (`templates/register.html`), but `app.py` currently only renders the form on GET — there is no POST handler, no validation, and no database insert. This step wires the existing form up to create real user accounts in the `users` table, hashing passwords with werkzeug and establishing a logged-in session so users can move on to the profile and expense-tracking steps.

## Depends on
Step 01 — Database Setup (users table, `get_db()`, `init_db()`, `seed_db()` in `database/db.py`) must be complete. It is.

## Routes
- GET /register – render the registration form (already exists, unchanged) – public
- POST /register – validate input, create the user, start a session, redirect to a logged-in page – public

## Database changes
No database changes. The existing `users` table (id, name, email, password_hash, created_at) already supports registration as defined in `database/db.py`.

## Templates
- Create: none
- Modify: `templates/register.html` — display validation/duplicate-email errors via the existing `{% if error %}` block (already wired up); no structural changes needed

## Files to change
- `app.py` — add POST handling to the `/register` route: read form fields, validate, check for existing email, hash password, insert user, set session, redirect

## Files to create
None

## New dependencies
No new dependencies. Uses `werkzeug.security.generate_password_hash` (already used in `database/db.py`) and Flask's built-in `session`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash` / `check_password_hash`)
- Use CSS variables – never hardcode hex values
- All templates extend base.html
- Validate required fields (name, email, password) server-side even though the form has `required` attributes client-side
- Reject registration with an email that already exists in `users` (return the form with an error, do not raise an unhandled exception)
- Set `app.secret_key` if not already configured, since sessions require it

## Definition of done
- [ ] Submitting the register form with a new name/email/password creates a row in `users` with a hashed password (verify via sqlite3 or a query script)
- [ ] Submitting with an email that already exists re-renders `register.html` with an error message and does not create a duplicate row
- [ ] Submitting with a missing field re-renders the form with an error instead of crashing
- [ ] After successful registration, the user is redirected away from `/register` (e.g. to `/profile` or landing) and a session is established
- [ ] Passwords are never stored or logged in plaintext
- [ ] App starts and `/register` GET still renders correctly with no errors
