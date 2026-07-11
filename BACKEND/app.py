"""
app.py
------
Flask application entry point.
Registers all routes, configures the app, and starts the dev server.
"""

import os
import sys

# Make sure BACKEND/ is on the Python path when app.py is run from the
# project root (e.g.  python BACKEND/app.py)
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, redirect, render_template, request, session, url_for

from account import InsufficientFundsError, apply_deposit, apply_withdrawal
from account import get_balance, get_recent_transactions
from auth import find_customer_by_id, find_customer_by_username
from auth import login_required, verify_password
from database import init_db

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)          # .../BACKEND
PROJECT_ROOT = os.path.dirname(BASE_DIR)      # .../banking-app

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "FRONTEND", "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "FRONTEND", "static"),
)

# SECRET_KEY: read from environment in production; use a safe fallback for dev.
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "dev-only-change-in-production-a9f2c4b7e1"
)

# Initialise database (create tables + seed) on startup.
init_db()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Redirect bare root URL to /login."""
    return redirect(url_for("login"))


# -- Authentication ----------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in -- skip the form.
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "GET":
        return render_template("login.html")

    # POST -- process credentials
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Validate inputs are not blank
    if not username or not password:
        return render_template(
            "login.html",
            error="Please enter your username and password."
        )

    customer = find_customer_by_username(username)

    # Use the same generic message for all failure cases to prevent
    # username enumeration attacks.
    if customer is None or not verify_password(customer.password, password):
        return render_template(
            "login.html",
            error="Invalid credentials. Please try again."
        )

    # Credentials valid -- create session
    session.clear()
    session["user_id"] = customer.id
    return redirect(url_for("dashboard"))


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


# -- Dashboard ---------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    customer = find_customer_by_id(session["user_id"])
    balance = get_balance(customer.id)
    recent_txns = get_recent_transactions(customer.id, limit=10)
    return render_template(
        "dashboard.html",
        customer=customer,
        balance=balance,
        transactions=recent_txns,
    )


# -- Deposit -----------------------------------------------------------------

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method == "GET":
        return render_template("deposit.html")

    # POST -- validate then apply
    raw_amount = request.form.get("amount", "").strip()

    if not raw_amount:
        return render_template("deposit.html", error="Please enter an amount.")

    try:
        amount = float(raw_amount)
    except ValueError:
        return render_template("deposit.html", error="Please enter a valid number.")

    if amount <= 0:
        return render_template("deposit.html", error="Amount must be greater than zero.")

    apply_deposit(session["user_id"], amount)
    return redirect(url_for("dashboard"))


# -- Withdraw ----------------------------------------------------------------

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    customer_id = session["user_id"]

    if request.method == "GET":
        balance = get_balance(customer_id)
        return render_template("withdraw.html", balance=balance)

    # POST -- read the form amount
    raw_amount = request.form.get("amount", "").strip()

    # Validation check 1: amount field must not be empty
    if not raw_amount:
        balance = get_balance(customer_id)
        return render_template("withdraw.html", balance=balance,
                               error="Amount is required")

    # Validation check 2: amount must be a positive number
    try:
        amount = float(raw_amount)
    except ValueError:
        amount = 0
    if amount <= 0:
        balance = get_balance(customer_id)
        return render_template("withdraw.html", balance=balance,
                               error="Amount must be greater than zero")

    # Validation check 3: amount must not exceed current balance
    balance = get_balance(customer_id)
    if amount > balance:
        return render_template("withdraw.html", balance=balance,
                               error="Insufficient funds")

    try:
        apply_withdrawal(customer_id, amount)
    except InsufficientFundsError as exc:
        balance = get_balance(customer_id)
        return render_template("withdraw.html", balance=balance, error=str(exc))

    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)