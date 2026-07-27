---
name: spendly-ui-designer
description: Generates modern, production-ready UI pages and components for Spendly, a personal expense tracker built with Flask (Jinja2 templates + static CSS/JS) — repo at rajesh-swarnkar/expenseTrackerPython3. Use this skill whenever the user asks to design, build, create, redesign, improve, restyle, or "make UI/UX for" any page or component in Spendly, even if they don't say "design" explicitly — e.g. "add a dashboard", "make the expense list nicer", "build the add-expense form", "polish the settings page". Always trigger for any front-end/visual work on Spendly, not just brand-new pages. Produces a brief UI-structure summary plus real Jinja2 template, CSS, and JS files matching the existing project layout (templates/, static/css/, static/js/), styled as a clean card-based fintech UI with Lucide icons.
---

# Spendly Frontend UI Designer

Generates modern, consistent UI pages/components for **Spendly**, a personal expense tracker (Flask + Jinja2 templates + static CSS/JS). Repo: `rajesh-swarnkar/expenseTrackerPython3`.

## Workflow

### Step 1 — Establish design context (do this before writing any code)

Design consistency is the top priority. Before generating anything:

1. **Check if the project is available on disk.** If the user is working inside the actual repo (files under `templates/`, `static/css/`, `static/js/`, `app.py` are visible), read the existing templates and CSS first. Extract the real design tokens already in use: color values, font-family, border-radius, spacing scale, shadow style, existing component patterns (nav bar, cards, buttons, forms). Reuse these exactly — don't invent new ones.
2. **If the project isn't available on disk, or the relevant existing pages aren't there yet**, ask the user for screenshots (or a link/description) of the current Spendly UI before styling anything new. Do not guess at a palette or generate final styling without this — this is a hard rule for this skill, not a soft preference.
   - Exception: if the user explicitly says something like "just use your best judgment" / "no reference, just make it look good" / "there's no existing design yet, propose one", proceed using the fallback design tokens in the "Fallback design tokens" section below, and tell the user you're doing so.
3. Once you have either (a) real extracted tokens or (b) explicit permission to use fallback tokens, move to Step 2.

### Step 2 — Clarify the request (only if genuinely ambiguous)

You need: which page/component, and any constraints (specific data fields, existing routes it must hook into, must-have states like empty/loading/error). If the user's request already makes this clear ("build the add-expense form with amount, category, date, note fields"), don't ask — proceed. Only ask when the component name/scope is actually unclear.

Check `app.py` for existing routes if present, so the generated template knows what URL/endpoint to post to or link from (`url_for(...)`), and check the base template (commonly `templates/base.html` or similar) to see if new pages should `{% extends %}` it.

### Step 3 — Produce the output

Every response from this skill has two parts, in this order:

**1. UI Structure (brief, in chat, not a huge essay)**
- Layout and key sections (e.g. "sticky top nav, summary cards row, filterable transaction table, floating add button")
- 3-5 notable UX decisions and why (e.g. "grouped by date with sticky sub-headers so long lists stay scannable")

**2. Code (as real files, matching repo structure)**
- Jinja2 template → `templates/<page_name>.html` (extend the existing base template if one exists; use `{% block %}` sections consistent with sibling templates)
- CSS → `static/css/<page_name>.css` if the project splits CSS per-page, otherwise append a clearly-commented section to the existing shared stylesheet — match whatever pattern the project already uses
- JS → `static/js/<page_name>.js` only if the component needs interactivity (filters, modals, live totals, form validation). Don't add JS for purely static pages.
- Keep CSS and JS modular and minimal — no unused boilerplate, no starter-kit cruft, no inline `style=` attributes.
- Save files with `create_file`/`str_replace` at their real repo-relative paths when working inside the project; otherwise create them under a clearly labeled output folder and tell the user where to drop them in.
- After creating the files, use `present_files` to hand them to the user. Don't paste the full file contents again in chat after already writing them to disk — the structure summary + the files is enough.

### Design rules (apply always)

- **Aesthetic**: minimal, clean fintech SaaS look. Card-based layout, generous whitespace, clear visual hierarchy (one obvious primary action per view).
- **Spacing**: stick to an 8px grid (8/16/24/32/48px) for padding, margins, and gaps. No arbitrary values like `13px` or `22px`.
- **Corners & depth**: rounded corners (typically 8-16px), soft/subtle box-shadows — never harsh drop shadows, never flat-and-bordered-only unless that's what the existing project already does.
- **Color**: subtle, restrained palette — a neutral base (grays/off-white) with one or two accent colors used sparingly for primary actions, positive/negative amounts (income vs. expense), and status. Never introduce a new accent color if the project already has one.
- **Icons**: use Lucide icons (https://lucide.dev) wherever an icon adds clarity — nav items, category tags, empty states, buttons. Load via the Lucide CDN/script already used in the project if present, otherwise add the standard Lucide script tag. Fall back to Heroicons only if the project already uses Heroicons elsewhere.
- **Typography**: consistent type scale, clear hierarchy between headings/labels/body/numbers. Financial figures (amounts) should stand out — larger size or weight, tabular/monospaced numerals if the project's font supports it.
- **Responsiveness**: layouts should hold up from mobile (~375px) to desktop. Card grids collapse to single column on small screens; tables become stacked cards or scroll horizontally rather than breaking.
- **States**: for anything showing data (lists, tables, charts), always design the empty state and, if relevant, a loading state — don't only design the "happy path with lots of data" case.

### Consistency rule

Match the existing Spendly design exactly wherever one already exists for a given surface (nav, buttons, cards, forms, colors, fonts, icon style). New pages should look like they were built by the same person on the same day as the rest of the app — not like a different app pasted in. When in doubt about whether something matches, prefer reusing an existing class/pattern over inventing a new one.

### Avoid

- Generic, dated, or "default Bootstrap-looking" UI.
- Unstructured code dumps — always lead with the brief structure summary before/alongside the code.
- Introducing a new CSS framework, JS framework, or icon set that isn't already in the project without checking with the user first (e.g. don't suddenly bring in Tailwind or React into a vanilla Flask/Jinja project).
- Overly busy layouts — if a page needs more than one primary call-to-action, reconsider the hierarchy.
- Inventing data or copy that contradicts what the user described (field names, categories, currency, etc.) — ask instead of guessing when it's not inferable from `app.py`/database schema.

## Fallback design tokens

Only use these when the user has explicitly opted out of providing screenshots/reference (see Step 1, exception case). State clearly to the user that these are placeholder tokens meant to be revisited once real screenshots are available.

- Font: `Inter`, system-ui fallback
- Base colors: `#0F172A` (text), `#64748B` (muted text), `#F8FAFC` (page bg), `#FFFFFF` (card bg), `#E2E8F0` (borders)
- Accent: `#4F46E5` (primary actions/links), `#059669` (income/positive), `#DC2626` (expense/negative)
- Radius: `12px` cards, `8px` buttons/inputs
- Shadow: `0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)`
- Spacing: 8px grid as described above
