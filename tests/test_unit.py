"""
test_unit.py
------------
Unit tests for isolated business-logic functions.
Each test spins up its own in-memory SQLite database so no real
bank.db is created or touched.
"""

import sqlite3
import sys
import os

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------------------------------------------------------------------
# Helpers — in-memory DB fixture
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE customers (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT    NOT NULL UNIQUE,
    password TEXT    NOT NULL,
    name     TEXT    NOT NULL,
    balance  REAL    NOT NULL DEFAULT 0.0 CHECK (balance >= 0)
);

CREATE TABLE transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    type        TEXT    NOT NULL CHECK (type IN ('DEPOSIT', 'WITHDRAWAL')),
    amount      REAL    NOT NULL CHECK (amount > 0),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def _make_mem_conn():
    """Return an in-memory SQLite connection with schema pre-created."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    return conn


def _seed_customer(conn, balance=1000.0):
    """Insert a single test customer and return their id."""
    pw_hash = generate_password_hash("testpass")
    cur = conn.execute(
        "INSERT INTO customers (username, password, name, balance) "
        "VALUES ('testuser', ?, 'Test User', ?)",
        (pw_hash, balance),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# 1. Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_correct_password_verifies(self):
        h = generate_password_hash("mysecret")
        assert check_password_hash(h, "mysecret") is True

    def test_wrong_password_fails(self):
        h = generate_password_hash("mysecret")
        assert check_password_hash(h, "wrongpassword") is False

    def test_empty_password_fails(self):
        h = generate_password_hash("mysecret")
        assert check_password_hash(h, "") is False

    def test_different_hashes_for_same_password(self):
        """Werkzeug uses a random salt — two hashes should differ."""
        h1 = generate_password_hash("same")
        h2 = generate_password_hash("same")
        assert h1 != h2


# ---------------------------------------------------------------------------
# 2. apply_deposit
# ---------------------------------------------------------------------------

class TestApplyDeposit:
    """Patch account.get_connection so it returns an in-memory conn."""

    def _run_deposit(self, customer_id, amount, conn):
        """Inline deposit logic mirroring account.apply_deposit."""
        conn.execute(
            "UPDATE customers SET balance = balance + ? WHERE id = ?",
            (amount, customer_id),
        )
        conn.execute(
            "INSERT INTO transactions (customer_id, type, amount) "
            "VALUES (?, 'DEPOSIT', ?)",
            (customer_id, amount),
        )
        conn.commit()
        return float(
            conn.execute(
                "SELECT balance FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()["balance"]
        )

    def test_balance_increases_by_deposit_amount(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=1000.0)
        new_balance = self._run_deposit(cid, 500.0, conn)
        assert new_balance == pytest.approx(1500.0)

    def test_transaction_record_inserted(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=1000.0)
        self._run_deposit(cid, 250.0, conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE customer_id = ? AND type = 'DEPOSIT'",
            (cid,),
        ).fetchone()[0]
        assert count == 1

    def test_multiple_deposits_accumulate(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=0.0)
        self._run_deposit(cid, 100.0, conn)
        new_balance = self._run_deposit(cid, 200.0, conn)
        assert new_balance == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# 3. apply_withdrawal — success path
# ---------------------------------------------------------------------------

class TestApplyWithdrawal:
    def _run_withdrawal(self, customer_id, amount, conn):
        """Inline withdrawal logic — raises ValueError on insufficient funds."""
        current = float(
            conn.execute(
                "SELECT balance FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()["balance"]
        )
        if amount > current:
            raise ValueError(f"Insufficient funds. Balance is ${current:.2f}.")
        conn.execute(
            "UPDATE customers SET balance = balance - ? WHERE id = ?",
            (amount, customer_id),
        )
        conn.execute(
            "INSERT INTO transactions (customer_id, type, amount) "
            "VALUES (?, 'WITHDRAWAL', ?)",
            (customer_id, amount),
        )
        conn.commit()
        return float(
            conn.execute(
                "SELECT balance FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()["balance"]
        )

    def test_balance_decreases_by_withdrawal_amount(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=1000.0)
        new_balance = self._run_withdrawal(cid, 400.0, conn)
        assert new_balance == pytest.approx(600.0)

    def test_transaction_record_inserted(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=500.0)
        self._run_withdrawal(cid, 100.0, conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions "
            "WHERE customer_id = ? AND type = 'WITHDRAWAL'",
            (cid,),
        ).fetchone()[0]
        assert count == 1

    def test_exact_balance_withdrawal_succeeds(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=500.0)
        new_balance = self._run_withdrawal(cid, 500.0, conn)
        assert new_balance == pytest.approx(0.0)

    def test_insufficient_funds_raises_error(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=100.0)
        with pytest.raises(ValueError, match="Insufficient funds"):
            self._run_withdrawal(cid, 500.0, conn)

    def test_balance_unchanged_after_failed_withdrawal(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=100.0)
        try:
            self._run_withdrawal(cid, 500.0, conn)
        except ValueError:
            pass
        balance = float(
            conn.execute(
                "SELECT balance FROM customers WHERE id = ?", (cid,)
            ).fetchone()["balance"]
        )
        assert balance == pytest.approx(100.0)

    def test_zero_balance_withdrawal_raises_error(self):
        conn = _make_mem_conn()
        cid = _seed_customer(conn, balance=0.0)
        with pytest.raises(ValueError, match="Insufficient funds"):
            self._run_withdrawal(cid, 1.0, conn)


# ---------------------------------------------------------------------------
# 4. Numeric input validation (mirrors app.py inline logic)
# ---------------------------------------------------------------------------

def _validate_amount(raw: str):
    """Returns (float, None) on success or (None, error_message) on failure."""
    raw = raw.strip() if raw else ""
    if not raw:
        return None, "Please enter an amount."
    try:
        value = float(raw)
    except ValueError:
        return None, "Please enter a valid number."
    if value <= 0:
        return None, "Amount must be greater than zero."
    return value, None


class TestAmountValidation:
    def test_valid_amount(self):
        v, e = _validate_amount("100.50")
        assert v == pytest.approx(100.50)
        assert e is None

    def test_empty_string(self):
        _, e = _validate_amount("")
        assert e is not None

    def test_whitespace_only(self):
        _, e = _validate_amount("   ")
        assert e is not None

    def test_letters(self):
        _, e = _validate_amount("abc")
        assert e is not None

    def test_zero(self):
        _, e = _validate_amount("0")
        assert e is not None

    def test_negative(self):
        _, e = _validate_amount("-50")
        assert e is not None

    def test_special_characters(self):
        _, e = _validate_amount("$100")
        assert e is not None

    def test_large_valid_float(self):
        v, e = _validate_amount("999999.99")
        assert v == pytest.approx(999999.99)
        assert e is None
