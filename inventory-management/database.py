"""
Database access layer: CRUD operations, stock automation, and analytics queries.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from config import get_connection
from models import (
    Category,
    LowStockAlert,
    Product,
    StockTransaction,
    Supplier,
    User,
)


class DatabaseError(Exception):
    """Base exception for database-related failures."""


class RecordNotFoundError(DatabaseError):
    """Raised when a requested record does not exist."""


class ValidationError(DatabaseError):
    """Raised when business validation fails."""


class InventoryDatabase:
    """
    Central repository for all inventory persistence and query operations.
    """

    PRODUCT_SELECT = """
        SELECT
            p.id, p.sku, p.name, p.description,
            p.category_id, p.supplier_id,
            p.unit_price, p.quantity, p.reorder_level,
            p.created_at, p.updated_at,
            c.name AS category_name,
            s.name AS supplier_name
        FROM products p
        INNER JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers s ON s.id = p.supplier_id
    """

    TRANSACTION_SELECT = """
        SELECT
            st.id, st.product_id, st.user_id,
            st.transaction_type, st.quantity_change,
            st.quantity_before, st.quantity_after,
            st.notes, st.created_at,
            p.name AS product_name,
            p.sku AS product_sku,
            u.username AS username
        FROM stock_transactions st
        INNER JOIN products p ON p.id = st.product_id
        LEFT JOIN users u ON u.id = st.user_id
    """

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fetchone(query: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        with get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()

    @staticmethod
    def _fetchall(query: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        with get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    @staticmethod
    def _execute(query: str, params: Tuple[Any, ...] = ()) -> int:
        with get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def create_user(self, username: str, email: str, role: str = "staff") -> User:
        user_id = self._execute(
            "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
            (username.strip(), email.strip(), role.strip()),
        )
        row = self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        return User.from_row(row)

    def get_all_users(self) -> List[User]:
        rows = self._fetchall("SELECT * FROM users ORDER BY username")
        return [User.from_row(row) for row in rows]

    def get_user_by_id(self, user_id: int) -> User:
        row = self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if row is None:
            raise RecordNotFoundError(f"User with id={user_id} not found.")
        return User.from_row(row)

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def create_category(self, name: str, description: Optional[str] = None) -> Category:
        category_id = self._execute(
            "INSERT INTO categories (name, description) VALUES (?, ?)",
            (name.strip(), description),
        )
        row = self._fetchone("SELECT * FROM categories WHERE id = ?", (category_id,))
        return Category.from_row(row)

    def get_all_categories(self) -> List[Category]:
        rows = self._fetchall("SELECT * FROM categories ORDER BY name")
        return [Category.from_row(row) for row in rows]

    def get_category_by_id(self, category_id: int) -> Category:
        row = self._fetchone("SELECT * FROM categories WHERE id = ?", (category_id,))
        if row is None:
            raise RecordNotFoundError(f"Category with id={category_id} not found.")
        return Category.from_row(row)

    def update_category(
        self, category_id: int, name: str, description: Optional[str] = None
    ) -> Category:
        updated = self._execute(
            "UPDATE categories SET name = ?, description = ? WHERE id = ?",
            (name.strip(), description, category_id),
        )
        if updated == 0:
            raise RecordNotFoundError(f"Category with id={category_id} not found.")
        return self.get_category_by_id(category_id)

    def delete_category(self, category_id: int) -> None:
        try:
            deleted = self._execute("DELETE FROM categories WHERE id = ?", (category_id,))
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                "Cannot delete category while products still reference it."
            ) from exc
        if deleted == 0:
            raise RecordNotFoundError(f"Category with id={category_id} not found.")

    # ------------------------------------------------------------------
    # Suppliers
    # ------------------------------------------------------------------

    def create_supplier(
        self,
        name: str,
        contact_person: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Supplier:
        supplier_id = self._execute(
            """
            INSERT INTO suppliers (name, contact_person, email, phone, address)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), contact_person, email, phone, address),
        )
        row = self._fetchone("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
        return Supplier.from_row(row)

    def get_all_suppliers(self) -> List[Supplier]:
        rows = self._fetchall("SELECT * FROM suppliers ORDER BY name")
        return [Supplier.from_row(row) for row in rows]

    def get_supplier_by_id(self, supplier_id: int) -> Supplier:
        row = self._fetchone("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
        if row is None:
            raise RecordNotFoundError(f"Supplier with id={supplier_id} not found.")
        return Supplier.from_row(row)

    def update_supplier(self, supplier_id: int, **fields: Any) -> Supplier:
        allowed = {"name", "contact_person", "email", "phone", "address"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            raise ValidationError("No valid supplier fields provided for update.")

        set_clause = ", ".join(f"{column} = ?" for column in updates)
        params = tuple(updates.values()) + (supplier_id,)
        changed = self._execute(
            f"UPDATE suppliers SET {set_clause} WHERE id = ?",
            params,
        )
        if changed == 0:
            raise RecordNotFoundError(f"Supplier with id={supplier_id} not found.")
        return self.get_supplier_by_id(supplier_id)

    def delete_supplier(self, supplier_id: int) -> None:
        deleted = self._execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
        if deleted == 0:
            raise RecordNotFoundError(f"Supplier with id={supplier_id} not found.")

    # ------------------------------------------------------------------
    # Products — CRUD
    # ------------------------------------------------------------------

    def create_product(
        self,
        sku: str,
        name: str,
        category_id: int,
        unit_price: float,
        quantity: int = 0,
        reorder_level: int = 10,
        supplier_id: Optional[int] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Product:
        self._validate_foreign_keys(category_id, supplier_id)

        product_id = self._execute(
            """
            INSERT INTO products
                (sku, name, description, category_id, supplier_id,
                 unit_price, quantity, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sku.strip().upper(),
                name.strip(),
                description,
                category_id,
                supplier_id,
                unit_price,
                quantity,
                reorder_level,
            ),
        )

        if quantity > 0:
            self._log_transaction(
                product_id=product_id,
                user_id=user_id,
                transaction_type="IN",
                quantity_change=quantity,
                quantity_before=0,
                quantity_after=quantity,
                notes="Initial stock on product creation",
            )

        product = self.get_product_by_id(product_id)
        if product.is_low_stock:
            raise LowStockAlert(
                product,
                f"WARNING: '{product.name}' is at or below reorder level "
                f"({product.quantity}/{product.reorder_level}).",
            )
        return product

    def get_all_products(self) -> List[Product]:
        rows = self._fetchall(f"{self.PRODUCT_SELECT} ORDER BY p.name")
        return [Product.from_row(row) for row in rows]

    def get_product_by_id(self, product_id: int) -> Product:
        row = self._fetchone(
            f"{self.PRODUCT_SELECT} WHERE p.id = ?",
            (product_id,),
        )
        if row is None:
            raise RecordNotFoundError(f"Product with id={product_id} not found.")
        return Product.from_row(row)

    def get_product_by_sku(self, sku: str) -> Product:
        row = self._fetchone(
            f"{self.PRODUCT_SELECT} WHERE p.sku = ?",
            (sku.strip().upper(),),
        )
        if row is None:
            raise RecordNotFoundError(f"Product with SKU '{sku}' not found.")
        return Product.from_row(row)

    def update_product(self, product_id: int, **fields: Any) -> Product:
        allowed = {
            "sku",
            "name",
            "description",
            "category_id",
            "supplier_id",
            "unit_price",
            "reorder_level",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            raise ValidationError("No valid product fields provided for update.")

        if "category_id" in updates or "supplier_id" in updates:
            current = self.get_product_by_id(product_id)
            self._validate_foreign_keys(
                updates.get("category_id", current.category_id),
                updates.get("supplier_id", current.supplier_id),
            )

        if "sku" in updates:
            updates["sku"] = str(updates["sku"]).strip().upper()

        set_clause = ", ".join(f"{column} = ?" for column in updates)
        params = tuple(updates.values()) + (product_id,)
        changed = self._execute(
            f"""
            UPDATE products
            SET {set_clause}, updated_at = datetime('now')
            WHERE id = ?
            """,
            params,
        )
        if changed == 0:
            raise RecordNotFoundError(f"Product with id={product_id} not found.")
        return self.get_product_by_id(product_id)

    def delete_product(self, product_id: int) -> None:
        try:
            deleted = self._execute("DELETE FROM products WHERE id = ?", (product_id,))
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                "Cannot delete product with existing transaction history."
            ) from exc
        if deleted == 0:
            raise RecordNotFoundError(f"Product with id={product_id} not found.")

    # ------------------------------------------------------------------
    # Stock management with automatic transaction logging
    # ------------------------------------------------------------------

    def update_stock(
        self,
        product_id: int,
        quantity_change: int,
        transaction_type: str,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Tuple[Product, StockTransaction]:
        """
        Adjust stock and automatically write an audit transaction.

        Raises:
            ValidationError: Invalid transaction type or insufficient stock.
            RecordNotFoundError: Product does not exist.
            LowStockAlert: Stock dropped to or below reorder level after update.
        """
        transaction_type = transaction_type.upper().strip()
        if transaction_type not in {"IN", "OUT", "ADJUSTMENT"}:
            raise ValidationError("transaction_type must be IN, OUT, or ADJUSTMENT.")

        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, quantity, reorder_level, name FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
            if row is None:
                raise RecordNotFoundError(f"Product with id={product_id} not found.")

            quantity_before = int(row["quantity"])
            reorder_level = int(row["reorder_level"])

            if transaction_type == "OUT" and quantity_change > quantity_before:
                raise ValidationError(
                    f"Insufficient stock. Available: {quantity_before}, "
                    f"requested removal: {quantity_change}."
                )

            if transaction_type == "ADJUSTMENT":
                quantity_after = quantity_change
                actual_change = quantity_after - quantity_before
            else:
                actual_change = quantity_change if transaction_type == "IN" else -quantity_change
                quantity_after = quantity_before + actual_change

            if quantity_after < 0:
                raise ValidationError("Resulting stock quantity cannot be negative.")

            conn.execute(
                """
                UPDATE products
                SET quantity = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (quantity_after, product_id),
            )

            cursor = conn.execute(
                """
                INSERT INTO stock_transactions
                    (product_id, user_id, transaction_type,
                     quantity_change, quantity_before, quantity_after, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    user_id,
                    transaction_type,
                    actual_change,
                    quantity_before,
                    quantity_after,
                    notes,
                ),
            )
            transaction_id = cursor.lastrowid
            conn.commit()

        product = self.get_product_by_id(product_id)
        transaction = self.get_transaction_by_id(transaction_id)

        if quantity_after <= reorder_level:
            raise LowStockAlert(
                product,
                f"ALERT: '{product.name}' stock is low "
                f"({quantity_after} <= reorder level {reorder_level}).",
            )

        return product, transaction

    def _log_transaction(
        self,
        product_id: int,
        user_id: Optional[int],
        transaction_type: str,
        quantity_change: int,
        quantity_before: int,
        quantity_after: int,
        notes: Optional[str],
    ) -> int:
        return self._execute(
            """
            INSERT INTO stock_transactions
                (product_id, user_id, transaction_type,
                 quantity_change, quantity_before, quantity_after, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                user_id,
                transaction_type,
                quantity_change,
                quantity_before,
                quantity_after,
                notes,
            ),
        )

    def get_transaction_by_id(self, transaction_id: int) -> StockTransaction:
        row = self._fetchone(
            f"{self.TRANSACTION_SELECT} WHERE st.id = ?",
            (transaction_id,),
        )
        if row is None:
            raise RecordNotFoundError(f"Transaction with id={transaction_id} not found.")
        return StockTransaction.from_row(row)

    # ------------------------------------------------------------------
    # Analytics / complex SQL queries
    # ------------------------------------------------------------------

    def get_total_inventory_value(self) -> Dict[str, Any]:
        """
        Calculate total inventory value using aggregation.
        """
        row = self._fetchone(
            """
            SELECT
                COUNT(p.id) AS product_count,
                COALESCE(SUM(p.quantity), 0) AS total_units,
                COALESCE(SUM(p.quantity * p.unit_price), 0.0) AS total_value
            FROM products p
            """
        )
        return {
            "product_count": int(row["product_count"]),
            "total_units": int(row["total_units"]),
            "total_value": round(float(row["total_value"]), 2),
        }

    def get_inventory_value_by_category(self) -> List[Dict[str, Any]]:
        rows = self._fetchall(
            """
            SELECT
                c.id AS category_id,
                c.name AS category_name,
                COUNT(p.id) AS product_count,
                COALESCE(SUM(p.quantity), 0) AS total_units,
                COALESCE(SUM(p.quantity * p.unit_price), 0.0) AS category_value
            FROM categories c
            LEFT JOIN products p ON p.category_id = c.id
            GROUP BY c.id, c.name
            ORDER BY category_value DESC
            """
        )
        return [
            {
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "product_count": int(row["product_count"]),
                "total_units": int(row["total_units"]),
                "category_value": round(float(row["category_value"]), 2),
            }
            for row in rows
        ]

    def get_low_stock_items(self, threshold: Optional[int] = None) -> List[Product]:
        """
        Return products at or below reorder level, or a custom threshold.
        """
        if threshold is None:
            query = f"""
                {self.PRODUCT_SELECT}
                WHERE p.quantity <= p.reorder_level
                ORDER BY p.quantity ASC, p.name ASC
            """
            rows = self._fetchall(query)
        else:
            query = f"""
                {self.PRODUCT_SELECT}
                WHERE p.quantity <= ?
                ORDER BY p.quantity ASC, p.name ASC
            """
            rows = self._fetchall(query, (threshold,))
        return [Product.from_row(row) for row in rows]

    def get_transaction_history(
        self,
        product_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[StockTransaction]:
        if product_id is None:
            rows = self._fetchall(
                f"""
                {self.TRANSACTION_SELECT}
                ORDER BY st.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        else:
            rows = self._fetchall(
                f"""
                {self.TRANSACTION_SELECT}
                WHERE st.product_id = ?
                ORDER BY st.created_at DESC
                LIMIT ?
                """,
                (product_id, limit),
            )
        return [StockTransaction.from_row(row) for row in rows]

    def get_top_products_by_value(self, limit: int = 5) -> List[Dict[str, Any]]:
        rows = self._fetchall(
            f"""
            SELECT
                p.id,
                p.sku,
                p.name,
                p.quantity,
                p.unit_price,
                (p.quantity * p.unit_price) AS line_value,
                c.name AS category_name
            FROM products p
            INNER JOIN categories c ON c.id = p.category_id
            ORDER BY line_value DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "id": row["id"],
                "sku": row["sku"],
                "name": row["name"],
                "quantity": int(row["quantity"]),
                "unit_price": float(row["unit_price"]),
                "line_value": round(float(row["line_value"]), 2),
                "category_name": row["category_name"],
            }
            for row in rows
        ]

    def get_supplier_stock_summary(self) -> List[Dict[str, Any]]:
        rows = self._fetchall(
            """
            SELECT
                s.id AS supplier_id,
                s.name AS supplier_name,
                COUNT(p.id) AS product_count,
                COALESCE(SUM(p.quantity), 0) AS total_units,
                COALESCE(SUM(p.quantity * p.unit_price), 0.0) AS stock_value
            FROM suppliers s
            LEFT JOIN products p ON p.supplier_id = s.id
            GROUP BY s.id, s.name
            ORDER BY stock_value DESC
            """
        )
        return [
            {
                "supplier_id": row["supplier_id"],
                "supplier_name": row["supplier_name"],
                "product_count": int(row["product_count"]),
                "total_units": int(row["total_units"]),
                "stock_value": round(float(row["stock_value"]), 2),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Internal validation
    # ------------------------------------------------------------------

    def _validate_foreign_keys(
        self, category_id: int, supplier_id: Optional[int]
    ) -> None:
        if self._fetchone("SELECT id FROM categories WHERE id = ?", (category_id,)) is None:
            raise ValidationError(f"Category id={category_id} does not exist.")
        if supplier_id is not None:
            if self._fetchone("SELECT id FROM suppliers WHERE id = ?", (supplier_id,)) is None:
                raise ValidationError(f"Supplier id={supplier_id} does not exist.")
