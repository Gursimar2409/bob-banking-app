"""
database.py
-----------
Handles SQLite connection, table creation, and test-data seeding.
All other modules obtain a connection by calling get_connection().
"""

import os
import sqlite3

from werkzeug.security import generate_password_hash

# Absolute path to bank.db sits alongside this file in BACKEND/
DB_PATH = os.path.join(os.path.dirname(__file__), "bank.db")


def get_connection() -> sqlite3.Connection:
    """Open and return a connection to bank.db.

    Row factory is set to sqlite3.Row so columns can be accessed by name
    (row['username']) as well as by index (row[0]).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enforce foreign-key constraints for every connection
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    """Create the customers and transactions tables if they don't exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            name     TEXT    NOT NULL,
            balance  REAL    NOT NULL DEFAULT 0.0
                             CHECK (balance >= 0)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL
                        REFERENCES customers(id),
            type        TEXT    NOT NULL
                        CHECK (type IN ('DEPOSIT', 'WITHDRAWAL')),
            amount      REAL    NOT NULL
                        CHECK (amount > 0),
            created_at  TEXT    NOT NULL
                        DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()


def _seed_customers(conn: sqlite3.Connection) -> None:
    """Insert test customers only when the table is empty (idempotent)."""
    count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    if count > 0:
        return  # Already seeded — nothing to do

    test_accounts = [
        ("alice",   "password123", "Alice Johnson", 5000.00),
        ("bob",     "password123", "Bob Smith",     3250.50),
        ("charlie", "password123", "Charlie Brown",  750.00),
    ]
    for username, plain_password, name, balance in test_accounts:
        conn.execute(
            "INSERT INTO customers (username, password, name, balance) "
            "VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(plain_password), name, balance),
        )
    conn.commit()


def init_db() -> None:
    """Public entry point called once at application startup.

    Creates tables and seeds test data if needed.
    """
    with get_connection() as conn:
        _create_tables(conn)
        _seed_customers(conn)
