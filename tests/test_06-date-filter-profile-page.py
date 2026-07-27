"""
Tests for Spec 06 — Date Filter for Profile Page.

Derived from `.claude/specs/06-date-filter-profile-page.md`: query-string
driven date filtering on GET /profile via `range` presets
(all/this_month/last_30/last_90/this_year) or a custom `start`/`end` pair.

These tests assert what the spec requires the *feature* to do — not what
app.py happens to do internally — so a spec violation (e.g. percentages
computed against the all-time total instead of the filtered total, or a
crash on malformed input) should surface as a failing test.

Each test seeds its own isolated sqlite database (via a temp DB_PATH patched
onto database.db before `app` is (re)imported) and its own user + expense
rows with known dates, so assertions are deterministic and don't depend on
the shared dev spendly.db.
"""
import re
import sys
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash


# --------------------------------------------------------------------- #
# Isolation fixtures                                                     #
# --------------------------------------------------------------------- #

@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    """Import a fresh `app` module bound to a throwaway sqlite DB file.

    database.db.DB_PATH is patched *before* `app` (re)runs its module-level
    init_db()/seed_db() calls, so this test run never touches the real
    dev spendly.db.
    """
    db_path = tmp_path / "test_spendly.db"

    import database.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))

    sys.modules.pop("app", None)
    import app as app_mod

    app_mod.app.config.update(TESTING=True)
    yield app_mod

    sys.modules.pop("app", None)


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def make_user(app_module, name="Filter Tester", email="filter-tester@example.com", password="password123"):
    conn = app_module.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def add_expense(app_module, user_id, amount, category, date_str, description=None):
    conn = app_module.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_str, description),
    )
    conn.commit()
    conn.close()


def login(client, user_id, user_name="Filter Tester"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = user_name


# --------------------------------------------------------------------- #
# HTML scraping helpers (scoped substring/regex search, not a DOM parser) #
# --------------------------------------------------------------------- #

def total_spent(html):
    m = re.search(r'Total spent</span>\s*<span class="profile-stat-value">\s*\D*?([\d.]+)\s*</span>', html, re.S)
    assert m, "could not find total spent value in rendered HTML"
    return float(m.group(1))


def transaction_count(html):
    m = re.search(r'Transactions</span>\s*<span class="profile-stat-value">\s*(\d+)\s*</span>', html, re.S)
    assert m, "could not find transaction count in rendered HTML"
    return int(m.group(1))


def top_category(html):
    m = re.search(r'Top category</span>\s*<span class="profile-stat-value">\s*([^<]+?)\s*</span>', html, re.S)
    assert m, "could not find top category value in rendered HTML"
    return m.group(1)


def breakdown_section(html):
    parts = html.split("Category breakdown")
    assert len(parts) > 1, "Category breakdown card not found"
    return parts[1]


def transactions_section(html):
    start = html.split("Recent transactions", 1)[1]
    return start.split("Category breakdown", 1)[0]


def category_rows(html):
    """Return list of (name, percent, total) tuples from the breakdown card."""
    section = breakdown_section(html)
    return re.findall(
        r'<span class="category-name">([^<]+)</span>.*?width:\s*([\d.]+)%.*?'
        r'<span class="category-total">\D*?([\d.]+)</span>',
        section,
        re.S,
    )


def transaction_rows(html):
    """Return list of (date, description, category, amount) from the recent txns table."""
    section = transactions_section(html)
    return re.findall(
        r'<td>([\d-]+)</td>\s*<td>([^<]*)</td>\s*<td><span class="badge[^"]*">([^<]+)</span></td>\s*'
        r'<td class="txn-amount">\D*?([\d.]+)</td>',
        section,
        re.S,
    )


def selected_range_option(html):
    m = re.search(r'<option value="(\w+)"[^>]*\bselected\b', html)
    return m.group(1) if m else None


def date_input_values(html):
    start_m = re.search(r'name="start"[^>]*value="([^"]*)"', html)
    end_m = re.search(r'name="end"[^>]*value="([^"]*)"', html)
    return (start_m.group(1) if start_m else ""), (end_m.group(1) if end_m else "")


def has_clear_link(html):
    return re.search(r'href="/profile"[^>]*>\s*Clear', html) is not None


# --------------------------------------------------------------------- #
# Routes / auth guard — spec says unaffected by this step                #
# --------------------------------------------------------------------- #

def test_profile_without_session_redirects_to_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_with_filter_query_params_still_requires_login(client):
    """Query-string filter params must not become a way to bypass auth."""
    resp = client.get("/profile?range=this_month&start=2026-01-01&end=2026-01-31")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# --------------------------------------------------------------------- #
# DoD: plain /profile behaves exactly as before this step                #
# --------------------------------------------------------------------- #

def test_no_query_params_shows_full_all_time_history(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 100.0, "Food", "2020-01-01")
    add_expense(app_module, user_id, 200.0, "Transport", "2021-06-15")
    add_expense(app_module, user_id, 300.0, "Bills", date.today().isoformat())

    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert total_spent(html) == pytest.approx(600.0)
    assert transaction_count(html) == 3


def test_default_range_query_param_is_all(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 50.0, "Food", "1999-01-01")

    resp = client.get("/profile?range=all")
    html = resp.get_data(as_text=True)
    assert total_spent(html) == pytest.approx(50.0)


def test_unknown_range_value_falls_back_to_all_time(client, app_module):
    """Spec only lists all/this_month/last_30/last_90/this_year as valid
    presets; an unrecognized value shouldn't crash or silently show nothing —
    it should behave like the unfiltered view."""
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 25.0, "Food", "2010-01-01")

    resp = client.get("/profile?range=not_a_real_preset")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert total_spent(html) == pytest.approx(25.0)


# --------------------------------------------------------------------- #
# DoD: preset ranges                                                     #
# --------------------------------------------------------------------- #

def test_this_month_preset_scopes_to_current_calendar_month(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    today = date.today()
    first_of_month = today.replace(day=1)
    prior_month_last_day = first_of_month - timedelta(days=1)

    add_expense(app_module, user_id, 111.0, "Food", first_of_month.isoformat(), "inside this month")
    add_expense(app_module, user_id, 222.0, "Transport", prior_month_last_day.isoformat(), "outside this month")

    resp = client.get("/profile?range=this_month")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert total_spent(html) == pytest.approx(111.0)
    assert transaction_count(html) == 1

    dates_shown = [r[0] for r in transaction_rows(html)]
    assert first_of_month.isoformat() in dates_shown
    assert prior_month_last_day.isoformat() not in dates_shown


def test_last_30_days_preset_scopes_to_trailing_window(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    today = date.today()
    recent = today - timedelta(days=10)
    stale = today - timedelta(days=100)

    add_expense(app_module, user_id, 40.0, "Food", recent.isoformat())
    add_expense(app_module, user_id, 90.0, "Bills", stale.isoformat())

    resp = client.get("/profile?range=last_30")
    html = resp.get_data(as_text=True)
    assert total_spent(html) == pytest.approx(40.0)
    assert transaction_count(html) == 1


def test_last_90_days_preset_scopes_to_trailing_window(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    today = date.today()
    recent = today - timedelta(days=40)      # within last 90, outside last 30
    stale = today - timedelta(days=200)      # outside last 90

    add_expense(app_module, user_id, 70.0, "Health", recent.isoformat())
    add_expense(app_module, user_id, 130.0, "Shopping", stale.isoformat())

    resp = client.get("/profile?range=last_90")
    html = resp.get_data(as_text=True)
    assert total_spent(html) == pytest.approx(70.0)
    assert transaction_count(html) == 1


def test_this_year_preset_scopes_to_current_calendar_year(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    today = date.today()
    this_year_jan = today.replace(month=1, day=1)
    last_year_dec = this_year_jan - timedelta(days=1)

    add_expense(app_module, user_id, 55.0, "Entertainment", this_year_jan.isoformat())
    add_expense(app_module, user_id, 66.0, "Other", last_year_dec.isoformat())

    resp = client.get("/profile?range=this_year")
    html = resp.get_data(as_text=True)
    assert total_spent(html) == pytest.approx(55.0)
    assert transaction_count(html) == 1


# --------------------------------------------------------------------- #
# DoD: custom start/end range                                            #
# --------------------------------------------------------------------- #

def test_custom_range_filters_all_four_sections_inclusively(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 10.0, "Food", "2020-05-09", "just before range")
    add_expense(app_module, user_id, 20.0, "Food", "2020-05-10", "on start boundary")
    add_expense(app_module, user_id, 30.0, "Transport", "2020-05-15", "middle of range")
    add_expense(app_module, user_id, 40.0, "Bills", "2020-05-20", "on end boundary")
    add_expense(app_module, user_id, 50.0, "Health", "2020-05-21", "just after range")

    resp = client.get("/profile?start=2020-05-10&end=2020-05-20")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200

    # Stats scoped to inclusive range: 20 + 30 + 40 = 90
    assert total_spent(html) == pytest.approx(90.0)
    assert transaction_count(html) == 3

    rows = transaction_rows(html)
    dates_shown = {r[0] for r in rows}
    assert "2020-05-10" in dates_shown
    assert "2020-05-20" in dates_shown
    assert "2020-05-09" not in dates_shown
    assert "2020-05-21" not in dates_shown

    cats = {row[0] for row in category_rows(html)}
    assert "Health" not in cats
    assert {"Food", "Transport", "Bills"} <= cats


def test_custom_start_end_take_precedence_over_range_param(client, app_module):
    """Spec: start/end are 'used instead of range when both are present and valid'."""
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 15.0, "Food", "2020-05-10")
    add_expense(app_module, user_id, 999.0, "Bills", date.today().isoformat())

    resp = client.get("/profile?range=this_month&start=2020-05-01&end=2020-05-31")
    html = resp.get_data(as_text=True)
    assert total_spent(html) == pytest.approx(15.0)
    assert transaction_count(html) == 1


def test_only_start_without_end_does_not_apply_custom_filter(client, app_module):
    """Spec requires both start and end to be present to use a custom range;
    a lone start (or lone end) should not silently filter open-ended."""
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 12.0, "Food", "2015-01-01")

    resp = client.get("/profile?start=2020-01-01")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    # Falls back to the default (all) view rather than crashing or silently
    # scoping to an open-ended range.
    assert total_spent(html) == pytest.approx(12.0)


def test_only_end_without_start_does_not_apply_custom_filter(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 12.0, "Food", "2015-01-01")

    resp = client.get("/profile?end=2020-01-01")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert total_spent(html) == pytest.approx(12.0)


# --------------------------------------------------------------------- #
# DoD: malformed / nonsensical custom ranges fall back to all-time        #
# --------------------------------------------------------------------- #

def test_start_after_end_falls_back_to_all_time_view(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 100.0, "Food", "2019-01-01")
    add_expense(app_module, user_id, 200.0, "Transport", "2023-06-01")

    all_time_resp = client.get("/profile")
    all_time_html = all_time_resp.get_data(as_text=True)

    resp = client.get("/profile?start=2023-01-01&end=2019-01-01")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert total_spent(html) == pytest.approx(total_spent(all_time_html))
    assert transaction_count(html) == transaction_count(all_time_html)


def test_malformed_custom_date_falls_back_to_all_time_view(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 100.0, "Food", "2019-01-01")
    add_expense(app_module, user_id, 200.0, "Transport", "2023-06-01")

    all_time_resp = client.get("/profile")
    all_time_html = all_time_resp.get_data(as_text=True)

    resp = client.get("/profile?start=not-a-date&end=2023-01-01")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert total_spent(html) == pytest.approx(total_spent(all_time_html))
    assert transaction_count(html) == transaction_count(all_time_html)


def test_wrong_format_custom_date_falls_back_to_all_time_view(client, app_module):
    """Dates must parse as YYYY-MM-DD; other formats must not crash the route."""
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 100.0, "Food", "2019-01-01")

    resp = client.get("/profile?start=01/15/2020&end=02/15/2020")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert total_spent(html) == pytest.approx(100.0)


def test_sql_injection_style_date_param_does_not_crash(client, app_module):
    """Rule: parameterised queries only — hostile query-string input must not
    break the route or leak an error page; malformed values should just fall
    back to the all-time view."""
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 100.0, "Food", "2019-01-01")

    resp = client.get("/profile?start=' OR '1'='1&end=2099-01-01")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert total_spent(html) == pytest.approx(100.0)


def test_empty_string_start_and_end_params_do_not_crash(client, app_module):
    """A blank date input submitted from the form (e.g. user picked a preset
    and left the date fields empty) should not be treated as a custom range."""
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 33.0, "Food", "2018-01-01")

    resp = client.get("/profile?range=all&start=&end=")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert total_spent(html) == pytest.approx(33.0)


# --------------------------------------------------------------------- #
# DoD: zero-match range                                                  #
# --------------------------------------------------------------------- #

def test_zero_match_range_shows_empty_state_not_an_error(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 100.0, "Food", "2020-01-01")

    resp = client.get("/profile?start=2021-01-01&end=2021-01-31")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "No expenses logged yet." in html
    assert "Nothing to break down yet." in html
    assert total_spent(html) == pytest.approx(0.0)
    assert transaction_count(html) == 0


def test_app_starts_and_renders_for_user_with_no_expenses_at_all(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "No expenses logged yet." in html
    assert "Nothing to break down yet." in html

    resp_filtered = client.get("/profile?range=this_month")
    assert resp_filtered.status_code == 200
    html_filtered = resp_filtered.get_data(as_text=True)
    assert "No expenses logged yet." in html_filtered
    assert "Nothing to break down yet." in html_filtered


# --------------------------------------------------------------------- #
# DoD: category percentages relative to filtered total                   #
# --------------------------------------------------------------------- #

def test_category_percentages_sum_to_100_of_filtered_total_not_all_time(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    # Inside the custom filter range: Food 30, Transport 70 -> total 100 in range.
    add_expense(app_module, user_id, 30.0, "Food", "2022-03-05")
    add_expense(app_module, user_id, 70.0, "Transport", "2022-03-10")
    # Outside the range: a large Bills expense that would dominate the
    # all-time total if percentages were (incorrectly) computed against it.
    add_expense(app_module, user_id, 900.0, "Bills", "2022-01-01")

    resp = client.get("/profile?start=2022-03-01&end=2022-03-31")
    html = resp.get_data(as_text=True)

    rows = category_rows(html)
    names = {r[0] for r in rows}
    assert "Bills" not in names

    percents = [float(r[1]) for r in rows]
    assert sum(percents) == pytest.approx(100.0, abs=1.5)

    totals = {r[0]: float(r[2]) for r in rows}
    assert totals["Food"] == pytest.approx(30.0)
    assert totals["Transport"] == pytest.approx(70.0)

    # Filtered total (used as percentage denominator) is 100, not the
    # all-time total of 1000.
    assert total_spent(html) == pytest.approx(100.0)


def test_top_category_reflects_filtered_range_not_all_time(client, app_module):
    """Top category stat is derived from the same grouped-by-category query
    that the breakdown card uses, so it must also be scoped to the range."""
    user_id = make_user(app_module)
    login(client, user_id)

    # All-time top category would be Bills (900), but it's outside the range.
    add_expense(app_module, user_id, 900.0, "Bills", "2022-01-01")
    add_expense(app_module, user_id, 70.0, "Transport", "2022-03-10")
    add_expense(app_module, user_id, 30.0, "Food", "2022-03-05")

    resp = client.get("/profile?start=2022-03-01&end=2022-03-31")
    html = resp.get_data(as_text=True)
    assert top_category(html) == "Transport"


# --------------------------------------------------------------------- #
# DoD: recent transactions still capped at 5, within the active range    #
# --------------------------------------------------------------------- #

def test_recent_transactions_still_capped_at_5_within_filtered_range(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    # 7 expenses within the filtered range; recent-transactions list must
    # still show only the 5 most recent of these, not all 7.
    for day, amount in zip(range(1, 8), [10, 20, 30, 40, 50, 60, 70]):
        add_expense(app_module, user_id, float(amount), "Food", f"2022-03-{day:02d}")
    # One expense outside the range that must never appear.
    add_expense(app_module, user_id, 999.0, "Bills", "2022-01-01")

    resp = client.get("/profile?start=2022-03-01&end=2022-03-31")
    html = resp.get_data(as_text=True)

    rows = transaction_rows(html)
    assert len(rows) == 5
    dates_shown = [r[0] for r in rows]
    # Most recent 5 within the range: 03-03 .. 03-07
    assert dates_shown == sorted(dates_shown, reverse=True)
    assert "2022-03-07" in dates_shown
    assert "2022-03-01" not in dates_shown
    assert "2022-01-01" not in dates_shown


# --------------------------------------------------------------------- #
# DoD: filter state reflected in the form on reload                      #
# --------------------------------------------------------------------- #

def test_preset_filter_reflected_as_selected_option_on_reload(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 10.0, "Food", date.today().isoformat())

    resp = client.get("/profile?range=last_30")
    html = resp.get_data(as_text=True)
    assert selected_range_option(html) == "last_30"


def test_all_time_reflected_as_selected_option_by_default(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 10.0, "Food", date.today().isoformat())

    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert selected_range_option(html) == "all"


def test_custom_range_reflected_in_date_inputs_on_reload(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 10.0, "Food", "2022-03-05")

    resp = client.get("/profile?start=2022-03-01&end=2022-03-31")
    html = resp.get_data(as_text=True)
    start_val, end_val = date_input_values(html)
    assert start_val == "2022-03-01"
    assert end_val == "2022-03-31"


def test_fallback_all_view_does_not_reflect_the_bad_custom_dates_submitted(client, app_module):
    """When malformed input falls back to all-time, the UI should reflect the
    *effective* filter (all), not echo back the nonsensical values that were
    submitted, per the spec's 'reflects the currently active filter' rule."""
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 10.0, "Food", "2018-01-01")

    resp = client.get("/profile?start=2023-01-01&end=2019-01-01")
    html = resp.get_data(as_text=True)
    assert selected_range_option(html) == "all"


# --------------------------------------------------------------------- #
# DoD: Clear control returns to unfiltered all-time view                 #
# --------------------------------------------------------------------- #

def test_clear_link_present_when_filtered_and_absent_when_all_time(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 10.0, "Food", date.today().isoformat())

    filtered_resp = client.get("/profile?range=this_month")
    filtered_html = filtered_resp.get_data(as_text=True)
    assert has_clear_link(filtered_html)

    plain_resp = client.get("/profile")
    plain_html = plain_resp.get_data(as_text=True)
    assert not has_clear_link(plain_html)


def test_following_clear_link_shows_full_all_time_history(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)

    add_expense(app_module, user_id, 100.0, "Food", "2019-01-01")
    add_expense(app_module, user_id, 200.0, "Transport", date.today().isoformat())

    # Simulate following the Clear link — plain GET /profile, no query params.
    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert total_spent(html) == pytest.approx(300.0)
    assert transaction_count(html) == 2
    assert selected_range_option(html) == "all"


# --------------------------------------------------------------------- #
# DoD: filtering never mutates data / app renders with no errors          #
# --------------------------------------------------------------------- #

def test_filtering_does_not_mutate_expense_rows(client, app_module):
    """Rule: filtering is read-only — applying any filter must never change
    row count or values in the expenses table."""
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 10.0, "Food", "2020-01-01")
    add_expense(app_module, user_id, 20.0, "Bills", "2021-06-01")

    conn = app_module.get_db()
    before = conn.execute(
        "SELECT date, amount, category FROM expenses ORDER BY id"
    ).fetchall()
    conn.close()

    client.get("/profile?range=this_month")
    client.get("/profile?start=2020-01-01&end=2020-01-01")
    client.get("/profile?start=bad&end=data")

    conn = app_module.get_db()
    after = conn.execute(
        "SELECT date, amount, category FROM expenses ORDER BY id"
    ).fetchall()
    conn.close()

    assert [tuple(r) for r in before] == [tuple(r) for r in after]


def test_profile_renders_with_no_errors_filtered_and_unfiltered(client, app_module):
    user_id = make_user(app_module)
    login(client, user_id)
    add_expense(app_module, user_id, 42.0, "Food", date.today().isoformat())

    for query in ("", "?range=all", "?range=this_month", "?range=last_30",
                  "?range=last_90", "?range=this_year",
                  "?start=2022-01-01&end=2022-12-31"):
        resp = client.get(f"/profile{query}")
        assert resp.status_code == 200, f"failed for query: {query!r}"