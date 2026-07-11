"""
account.py
----------
Service layer for account queries and fund movements.
This is the single authoritative place where balances are read or
changed. No other module may query or UPDATE the customers table
balance column directly.
"""

from typing import List, Tuple

from database import get_connection
from models import Transaction


class InsufficientFundsError(Exception):
    """Raised by apply_withdrawal when the balance is too low."""


def get_balance(customer_id: int) -> float:
    """Return the current account balance for the given customer."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT balance FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"No customer found with id={customer_id}")
        return float(row["balance"])
    finally:
        conn.close()


def get_recent_transactions(customer_id: int, limit: int = 10) -> List[Transaction]:
    """Return the most recent `limit` transactions, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM transactions
            WHERE  customer_id = ?
            ORDER  BY id DESC
            LIMIT  ?
            """,
            (customer_id, limit),
        ).fetchall()
        return [Transaction.from_row(row) for row in rows]
    finally:
        conn.close()


def apply_deposit(customer_id: int, amount: float) -> float:
    """Add `amount` to the customer's balance and record a DEPOSIT transaction.

    Both the balance update and the transaction insert run inside a single
    database transaction — either both succeed or neither does.

    Returns the new balance.
    """
    conn = get_connection()
    try:
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
        new_balance = conn.execute(
            "SELECT balance FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()["balance"]
        return float(new_balance)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_withdrawal(customer_id: int, amount: float) -> float:
    """Deduct `amount` from the balance and record a WITHDRAWAL transaction.

    Raises InsufficientFundsError if the balance would go below zero.
    Both the balance update and the transaction insert run inside a single
    database transaction.

    Returns the new balance.
    """
    conn = get_connection()
    try:
        current = float(
            conn.execute(
                "SELECT balance FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()["balance"]
        )
        if amount > current:
            raise InsufficientFundsError(
                f"Insufficient funds. Your current balance is ${current:,.2f}."
            )
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
        new_balance = conn.execute(
            "SELECT balance FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()["balance"]
        return float(new_balance)
    except InsufficientFundsError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
