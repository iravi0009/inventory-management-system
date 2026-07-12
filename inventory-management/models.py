"""
Object-oriented domain models for the Inventory Management System.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Convert SQLite datetime strings into Python datetime objects."""
    if value is None:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@dataclass
class User:
    """Represents a system user."""

    id: Optional[int] = None
    username: str = ""
    email: str = ""
    role: str = "staff"
    created_at: Optional[datetime] = field(default=None, repr=False)

    @classmethod
    def from_row(cls, row: Any) -> "User":
        return cls(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            role=row["role"],
            created_at=_parse_datetime(row["created_at"]),
        )


@dataclass
class Category:
    """Represents a product category."""

    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime] = field(default=None, repr=False)

    @classmethod
    def from_row(cls, row: Any) -> "Category":
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=_parse_datetime(row["created_at"]),
        )


@dataclass
class Supplier:
    """Represents a product supplier."""

    id: Optional[int] = None
    name: str = ""
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[datetime] = field(default=None, repr=False)

    @classmethod
    def from_row(cls, row: Any) -> "Supplier":
        return cls(
            id=row["id"],
            name=row["name"],
            contact_person=row["contact_person"],
            email=row["email"],
            phone=row["phone"],
            address=row["address"],
            created_at=_parse_datetime(row["created_at"]),
        )


@dataclass
class Product:
    """Represents an inventory product."""

    id: Optional[int] = None
    sku: str = ""
    name: str = ""
    description: Optional[str] = None
    category_id: int = 0
    supplier_id: Optional[int] = None
    unit_price: float = 0.0
    quantity: int = 0
    reorder_level: int = 10
    created_at: Optional[datetime] = field(default=None, repr=False)
    updated_at: Optional[datetime] = field(default=None, repr=False)

    # Enriched fields from JOIN queries (not stored directly on products table)
    category_name: Optional[str] = field(default=None, repr=False)
    supplier_name: Optional[str] = field(default=None, repr=False)

    @property
    def inventory_value(self) -> float:
        """Calculate total value of current stock for this product."""
        return round(self.unit_price * self.quantity, 2)

    @property
    def is_low_stock(self) -> bool:
        """Return True when quantity is at or below the reorder level."""
        return self.quantity <= self.reorder_level

    @classmethod
    def from_row(cls, row: Any) -> "Product":
        keys = row.keys()
        return cls(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            description=row["description"],
            category_id=row["category_id"],
            supplier_id=row["supplier_id"],
            unit_price=float(row["unit_price"]),
            quantity=int(row["quantity"]),
            reorder_level=int(row["reorder_level"]),
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
            category_name=row["category_name"] if "category_name" in keys else None,
            supplier_name=row["supplier_name"] if "supplier_name" in keys else None,
        )


@dataclass
class StockTransaction:
    """Represents a stock movement audit record."""

    id: Optional[int] = None
    product_id: int = 0
    user_id: Optional[int] = None
    transaction_type: str = "ADJUSTMENT"
    quantity_change: int = 0
    quantity_before: int = 0
    quantity_after: int = 0
    notes: Optional[str] = None
    created_at: Optional[datetime] = field(default=None, repr=False)

    # Enriched fields from JOIN queries
    product_name: Optional[str] = field(default=None, repr=False)
    product_sku: Optional[str] = field(default=None, repr=False)
    username: Optional[str] = field(default=None, repr=False)

    @classmethod
    def from_row(cls, row: Any) -> "StockTransaction":
        keys = row.keys()
        return cls(
            id=row["id"],
            product_id=row["product_id"],
            user_id=row["user_id"],
            transaction_type=row["transaction_type"],
            quantity_change=int(row["quantity_change"]),
            quantity_before=int(row["quantity_before"]),
            quantity_after=int(row["quantity_after"]),
            notes=row["notes"],
            created_at=_parse_datetime(row["created_at"]),
            product_name=row["product_name"] if "product_name" in keys else None,
            product_sku=row["product_sku"] if "product_sku" in keys else None,
            username=row["username"] if "username" in keys else None,
        )


class LowStockAlert(Exception):
    """Raised as a warning signal when stock falls below the reorder threshold."""

    def __init__(self, product: Product, message: str) -> None:
        self.product = product
        self.message = message
        super().__init__(message)
