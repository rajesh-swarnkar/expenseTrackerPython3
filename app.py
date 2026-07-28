import sqlite3
from datetime import datetime, timedelta

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import CATEGORIES, get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def format_member_since(created_at):
    try:
        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return created_at or "—"
    return dt.strftime("%B %Y")


def get_initials(name):
    parts = name.split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def resolve_date_range(range_key, start, end):
    today = datetime.now().date()

    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            return {"start": None, "end": None, "range": "all", "start_input": "", "end_input": ""}
        if start_date > end_date:
            return {"start": None, "end": None, "range": "all", "start_input": "", "end_input": ""}
        return {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "range": "custom",
            "start_input": start,
            "end_input": end,
        }

    presets = {
        "this_month": today.replace(day=1),
        "last_30": today - timedelta(days=29),
        "last_90": today - timedelta(days=89),
        "this_year": today.replace(month=1, day=1),
    }
    if range_key in presets:
        return {
            "start": presets[range_key].isoformat(),
            "end": today.isoformat(),
            "range": range_key,
            "start_input": "",
            "end_input": "",
        }

    return {"start": None, "end": None, "range": "all", "start_input": "", "end_input": ""}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template(
            "register.html", error="All fields are required.", name=name, email=email
        )

    if "@" not in email:
        return render_template(
            "register.html", error="Enter a valid email address.", name=name, email=email
        )

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must be at least 8 characters.",
            name=name,
            email=email,
        )

    conn = get_db()
    existing = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return render_template(
            "register.html",
            error="An account with this email already exists.",
            name=name,
            email=email,
        )

    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return render_template(
            "register.html",
            error="An account with this email already exists.",
            name=name,
            email=email,
        )
    conn.close()

    session["user_id"] = user_id
    session["user_name"] = name
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "login.html", error="Email and password are required.", email=email
        )

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error="Invalid email or password.", email=email
        )

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    conn = get_db()
    user_row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user_row:
        conn.close()
        session.clear()
        return redirect(url_for("login"))

    date_filter = resolve_date_range(
        request.args.get("range", "all"),
        request.args.get("start"),
        request.args.get("end"),
    )

    where_clause = "user_id = ?"
    params = [user_id]
    if date_filter["start"] and date_filter["end"]:
        where_clause += " AND date BETWEEN ? AND ?"
        params.extend([date_filter["start"], date_filter["end"]])
    params = tuple(params)

    totals = conn.execute(
        f"SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM expenses WHERE {where_clause}",
        params,
    ).fetchone()
    total_spent = totals["total"]
    transaction_count = totals["count"]

    category_totals = conn.execute(
        f"""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE {where_clause}
        GROUP BY category
        ORDER BY total DESC
        """,
        params,
    ).fetchall()

    recent = conn.execute(
        f"""
        SELECT id, date, description, category, amount
        FROM expenses
        WHERE {where_clause}
        ORDER BY date DESC, id DESC
        LIMIT 5
        """,
        params,
    ).fetchall()
    conn.close()

    user = {
        "initials": get_initials(user_row["name"]),
        "name": user_row["name"],
        "email": user_row["email"],
        "member_since": format_member_since(user_row["created_at"]),
    }

    stats = {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "top_category": category_totals[0]["category"] if category_totals else "—",
    }

    categories = [
        {
            "name": row["category"],
            "total": row["total"],
            "percent": round((row["total"] / total_spent) * 100, 1) if total_spent else 0,
        }
        for row in category_totals
    ]

    transactions = [
        {
            "id": row["id"],
            "date": row["date"],
            "description": row["description"] or "—",
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in recent
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        categories=categories,
        transactions=transactions,
        filter=date_filter,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("add_expense.html", categories=CATEGORIES)

    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    error = None
    amount_value = None
    try:
        amount_value = float(amount)
        if amount_value <= 0:
            raise ValueError
    except ValueError:
        error = "Enter a valid amount greater than zero."

    if not error and category not in CATEGORIES:
        error = "Select a valid category."

    if not error:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            error = "Enter a valid date."

    if error:
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            error=error,
            amount=amount,
            category=category,
            date=date,
            description=description,
        )

    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount_value, category, date, description or None),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("profile"))


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    conn = get_db()
    expense = conn.execute(
        "SELECT id, amount, category, date, description FROM expenses WHERE id = ? AND user_id = ?",
        (id, user_id),
    ).fetchone()
    conn.close()

    if not expense:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            categories=CATEGORIES,
            expense_id=id,
            amount=f"{expense['amount']:.2f}",
            category=expense["category"],
            date=expense["date"],
            description=expense["description"],
        )

    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    error = None
    amount_value = None
    try:
        amount_value = float(amount)
        if amount_value <= 0:
            raise ValueError
    except ValueError:
        error = "Enter a valid amount greater than zero."

    if not error and category not in CATEGORIES:
        error = "Select a valid category."

    if not error:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            error = "Enter a valid date."

    if error:
        return render_template(
            "edit_expense.html",
            categories=CATEGORIES,
            expense_id=id,
            error=error,
            amount=amount,
            category=category,
            date=date,
            description=description,
        )

    conn = get_db()
    conn.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?",
        (amount_value, category, date, description or None, id, user_id),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
