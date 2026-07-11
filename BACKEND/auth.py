"""
auth.py
-------
Authentication helpers and the login_required route decorator.
All identity logic is centralised here so no other module needs to
know how credentials are stored or sessions are managed.
"""

from functools import wraps
from typing import Optional

from flask import redirect, session, url_for
from werkzeug.security import check_password_hash

from database import get_connection
from models import Customer


def find_customer_by_username(username: str) -> Optional[Customer]:
    """Return the Customer whose username matches, or None if not found.

    Performs a case-sensitive exact match (SQLite TEXT comparison).
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE username = ?", (username,)
        ).fetchone()
        return Customer.from_row(row) if row else None
    finally:
        conn.close()


def find_customer_by_id(customer_id: int) -> Optional[Customer]:
    """Return the Customer with the given primary key, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        return Customer.from_row(row) if row else None
    finally:
        conn.close()


def verify_password(stored_hash: str, submitted_password: str) -> bool:
    """Return True if submitted_password matches the stored bcrypt hash.

    Uses Werkzeug's check_password_hash — never compare plain strings.
    """
    return check_password_hash(stored_hash, submitted_password)


def login_required(f):
    """Route decorator: redirect to /login if the session has no user_id.

    Usage::

        @app.route('/dashboard')
        @login_required
        def dashboard():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function
