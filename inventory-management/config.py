"""
Database configuration and schema initialization for the Inventory Management System.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & settings
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "inventory.db"

DEFAULT_LOW_STOCK_THRESHOLD = 10
DEFAULT_REORDER_LEVEL = 10


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite connection with foreign keys enabled.

    Returns:
        sqlite3.Connection: Active database connection with Row factory.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    email       TEXT    NOT NULL UNIQUE,
    role        TEXT    NOT NULL DEFAULT 'staff'
                        CHECK(role IN ('admin', 'manager', 'staff')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    contact_person  TEXT,
    email           TEXT,
    phone           TEXT,
    address         TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sku             TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    description     TEXT,
    category_id     INTEGER NOT NULL,
    supplier_id     INTEGER,
    unit_price      REAL    NOT NULL DEFAULT 0.0
                            CHECK(unit_price >= 0),
    quantity        INTEGER NOT NULL DEFAULT 0
                            CHECK(quantity >= 0),
    reorder_level   INTEGER NOT NULL DEFAULT 10
                            CHECK(reorder_level >= 0),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES categories(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS stock_transactions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id        INTEGER NOT NULL,
    user_id           INTEGER,
    transaction_type  TEXT    NOT NULL
                              CHECK(transaction_type IN ('IN', 'OUT', 'ADJUSTMENT')),
    quantity_change   INTEGER NOT NULL,
    quantity_before   INTEGER NOT NULL,
    quantity_after    INTEGER NOT NULL,
    notes             TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products(category_id);

CREATE INDEX IF NOT EXISTS idx_products_supplier
    ON products(supplier_id);

CREATE INDEX IF NOT EXISTS idx_stock_transactions_product
    ON stock_transactions(product_id);

CREATE INDEX IF NOT EXISTS idx_stock_transactions_created
    ON stock_transactions(created_at);
"""


def initialize_database(seed_sample_data: bool = True) -> None:
    """
    Create all tables and optionally insert seed data for demonstration.

    Args:
        seed_sample_data: When True, populate the database with sample records
                          if no users exist yet.
    """
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)

        if seed_sample_data:
            cursor = conn.execute("SELECT COUNT(*) AS count FROM users")
            if cursor.fetchone()["count"] == 0:
                _seed_sample_data(conn)

        conn.commit()


def _seed_sample_data(conn: sqlite3.Connection) -> None:
    """Insert starter records so the CLI is usable immediately."""
    conn.executemany(
        "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
        [
            ("admin", "admin@inventory.local", "admin"),
            ("jsmith", "jsmith@inventory.local", "manager"),
            ("awhite", "awhite@inventory.local", "staff"),
        ],
    )

    conn.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        [
            ("Electronics", "Electronic devices and accessories"),
            ("Office Supplies", "Stationery and office consumables"),
            ("Furniture", "Desks, chairs, and storage"),
        ],
    )

    conn.executemany(
        "INSERT INTO suppliers (name, contact_person, email, phone, address) VALUES (?, ?, ?, ?, ?)",
        [
            ("TechSource Ltd", "Jane Doe", "jane@techsource.com", "555-0101", "12 Tech Park"),
            ("OfficeMax", "John Roe", "john@officemax.com", "555-0202", "45 Supply Lane"),
            ("FurniCo", "Mary Lane", "mary@furnico.com", "555-0303", "78 Warehouse Rd"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO products
            (sku, name, description, category_id, supplier_id, unit_price, quantity, reorder_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("ELEC-001", "Wireless Mouse", "Ergonomic wireless mouse", 1, 1, 24.99, 45, 10),
            ("ELEC-002", "USB-C Hub", "7-in-1 USB-C adapter", 1, 1, 39.99, 8, 15),
            ("OFF-001", "A4 Paper Ream", "500 sheets, 80gsm", 2, 2, 5.49, 120, 20),
            ("OFF-002", "Ballpoint Pens (Box)", "Box of 50 blue pens", 2, 2, 12.00, 5, 10),
            ("FURN-001", "Office Chair", "Adjustable mesh chair", 3, 3, 199.99, 12, 5),
        ],
    )
