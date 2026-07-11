"""
models.py
---------
Plain Python data containers that represent database rows.
No database logic lives here — these objects are constructed by the
service/auth layers and passed up to route handlers and templates.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Customer:
    """Represents a row in the customers table."""

    id: int
    username: str
    password: str          # hashed — never expose to templates
    name: str
    balance: float

    @classmethod
    def from_row(cls, row) -> "Customer":
        """Construct a Customer from a sqlite3.Row (or any mapping)."""
        return cls(
            id=row["id"],
            username=row["username"],
            password=row["password"],
            name=row["name"],
            balance=row["balance"],
        )


@dataclass
class Transaction:
    """Represents a row in the transactions table."""

    id: int
    customer_id: int
    type: str              # 'DEPOSIT' or 'WITHDRAWAL'
    amount: float
    created_at: str        # ISO-8601 string from SQLite datetime()

    @classmethod
    def from_row(cls, row) -> "Transaction":
        """Construct a Transaction from a sqlite3.Row (or any mapping)."""
        return cls(
            id=row["id"],
            customer_id=row["customer_id"],
            type=row["type"],
            amount=row["amount"],
            created_at=row["created_at"],
        )
