"""
Command-line interface for the Inventory Management System.
"""

from __future__ import annotations

import sys
from typing import Callable, List, Optional

from tabulate import tabulate

from config import initialize_database
from database import (
    DatabaseError,
    InventoryDatabase,
    RecordNotFoundError,
    ValidationError,
)
from models import LowStockAlert, Product


class InventoryCLI:
    """Interactive terminal application for inventory operations."""

    def __init__(self) -> None:
        self.db = InventoryDatabase()
        self.current_user_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def clear_screen() -> None:
        print("\n" * 2)

    @staticmethod
    def pause() -> None:
        input("\nPress Enter to continue...")

    @staticmethod
    def prompt(message: str, default: Optional[str] = None) -> str:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{message}{suffix}: ").strip()
        return value if value else (default or "")

    @staticmethod
    def prompt_int(message: str, default: Optional[int] = None) -> int:
        while True:
            raw = InventoryCLI.prompt(
                message,
                str(default) if default is not None else None,
            )
            try:
                return int(raw)
            except ValueError:
                print("Please enter a valid integer.")

    @staticmethod
    def prompt_float(message: str, default: Optional[float] = None) -> float:
        while True:
            raw = InventoryCLI.prompt(
                message,
                str(default) if default is not None else None,
            )
            try:
                return float(raw)
            except ValueError:
                print("Please enter a valid number.")

    @staticmethod
    def print_error(exc: Exception) -> None:
        print(f"\n[ERROR] {exc}")

    @staticmethod
    def print_warning(message: str) -> None:
        print(f"\n[WARNING] {message}")

    @staticmethod
    def print_success(message: str) -> None:
        print(f"\n[SUCCESS] {message}")

    def handle_low_stock_alert(self, exc: LowStockAlert) -> None:
        self.print_warning(exc.message)

    # ------------------------------------------------------------------
    # Display tables
    # ------------------------------------------------------------------

    @staticmethod
    def display_products(products: List[Product]) -> None:
        if not products:
            print("\nNo products found.")
            return

        rows = [
            [
                p.id,
                p.sku,
                p.name,
                p.category_name or p.category_id,
                p.supplier_name or "-",
                f"${p.unit_price:.2f}",
                p.quantity,
                p.reorder_level,
                "LOW" if p.is_low_stock else "OK",
            ]
            for p in products
        ]
        print(
            tabulate(
                rows,
                headers=[
                    "ID",
                    "SKU",
                    "Name",
                    "Category",
                    "Supplier",
                    "Price",
                    "Qty",
                    "Reorder",
                    "Status",
                ],
                tablefmt="grid",
            )
        )

    # ------------------------------------------------------------------
    # User session
    # ------------------------------------------------------------------

    def select_user(self) -> None:
        users = self.db.get_all_users()
        print("\nSelect active user:")
        for user in users:
            print(f"  {user.id}. {user.username} ({user.role})")

        user_id = self.prompt_int("Enter user ID", default=users[0].id)
        try:
            user = self.db.get_user_by_id(user_id)
            self.current_user_id = user.id
            self.print_success(f"Logged in as {user.username} ({user.role}).")
        except RecordNotFoundError as exc:
            self.print_error(exc)

    # ------------------------------------------------------------------
    # Product menus
    # ------------------------------------------------------------------

    def menu_products(self) -> None:
        actions = {
            "1": ("List all products", self.action_list_products),
            "2": ("Add product", self.action_add_product),
            "3": ("View product", self.action_view_product),
            "4": ("Update product", self.action_update_product),
            "5": ("Delete product", self.action_delete_product),
            "6": ("Back", None),
        }

        while True:
            self.clear_screen()
            print("=== Product Management ===")
            for key, (label, _) in actions.items():
                print(f"  {key}. {label}")

            choice = self.prompt("Choose an option")
            if choice == "6":
                return

            action = actions.get(choice, (None, None))[1]
            if action is None:
                print("Invalid choice.")
                self.pause()
                continue

            try:
                action()
            except (DatabaseError, ValueError) as exc:
                self.print_error(exc)
            except LowStockAlert as exc:
                self.handle_low_stock_alert(exc)
            self.pause()

    def action_list_products(self) -> None:
        products = self.db.get_all_products()
        self.display_products(products)

    def action_add_product(self) -> None:
        print("\n--- Add New Product ---")
        categories = self.db.get_all_categories()
        suppliers = self.db.get_all_suppliers()

        print("\nCategories:")
        for c in categories:
            print(f"  {c.id}. {c.name}")
        print("\nSuppliers:")
        for s in suppliers:
            print(f"  {s.id}. {s.name}")

        sku = self.prompt("SKU")
        name = self.prompt("Product name")
        description = self.prompt("Description (optional)", default="")
        category_id = self.prompt_int("Category ID")
        supplier_raw = self.prompt("Supplier ID (optional)", default="")
        supplier_id = int(supplier_raw) if supplier_raw else None
        unit_price = self.prompt_float("Unit price")
        quantity = self.prompt_int("Initial quantity", default=0)
        reorder_level = self.prompt_int("Reorder level", default=10)

        product = self.db.create_product(
            sku=sku,
            name=name,
            description=description or None,
            category_id=category_id,
            supplier_id=supplier_id,
            unit_price=unit_price,
            quantity=quantity,
            reorder_level=reorder_level,
            user_id=self.current_user_id,
        )
        self.print_success(f"Product '{product.name}' created with ID {product.id}.")

    def action_view_product(self) -> None:
        product_id = self.prompt_int("Product ID")
        product = self.db.get_product_by_id(product_id)
        print(
            tabulate(
                [
                    ["ID", product.id],
                    ["SKU", product.sku],
                    ["Name", product.name],
                    ["Description", product.description or "-"],
                    ["Category", product.category_name],
                    ["Supplier", product.supplier_name or "-"],
                    ["Unit Price", f"${product.unit_price:.2f}"],
                    ["Quantity", product.quantity],
                    ["Reorder Level", product.reorder_level],
                    ["Inventory Value", f"${product.inventory_value:.2f}"],
                    ["Status", "LOW STOCK" if product.is_low_stock else "OK"],
                ],
                tablefmt="plain",
            )
        )

    def action_update_product(self) -> None:
        product_id = self.prompt_int("Product ID to update")
        print("Leave blank to keep current value.")

        sku = self.prompt("New SKU", default="")
        name = self.prompt("New name", default="")
        description = self.prompt("New description", default="")
        unit_price_raw = self.prompt("New unit price", default="")
        reorder_raw = self.prompt("New reorder level", default="")

        fields = {}
        if sku:
            fields["sku"] = sku
        if name:
            fields["name"] = name
        if description:
            fields["description"] = description
        if unit_price_raw:
            fields["unit_price"] = float(unit_price_raw)
        if reorder_raw:
            fields["reorder_level"] = int(reorder_raw)

        product = self.db.update_product(product_id, **fields)
        self.print_success(f"Product '{product.name}' updated.")

    def action_delete_product(self) -> None:
        product_id = self.prompt_int("Product ID to delete")
        confirm = self.prompt("Type DELETE to confirm", default="")
        if confirm != "DELETE":
            print("Deletion cancelled.")
            return
        self.db.delete_product(product_id)
        self.print_success(f"Product ID {product_id} deleted.")

    # ------------------------------------------------------------------
    # Stock menus
    # ------------------------------------------------------------------

    def menu_stock(self) -> None:
        actions = {
            "1": ("Stock IN (receive)", lambda: self.action_stock("IN")),
            "2": ("Stock OUT (dispatch)", lambda: self.action_stock("OUT")),
            "3": ("Stock ADJUSTMENT (set exact qty)", lambda: self.action_stock("ADJUSTMENT")),
            "4": ("Back", None),
        }

        while True:
            self.clear_screen()
            print("=== Stock Operations ===")
            for key, (label, _) in actions.items():
                print(f"  {key}. {label}")

            choice = self.prompt("Choose an option")
            if choice == "4":
                return

            action = actions.get(choice, (None, None))[1]
            if action is None:
                print("Invalid choice.")
                self.pause()
                continue

            try:
                action()
            except (DatabaseError, ValueError) as exc:
                self.print_error(exc)
            except LowStockAlert as exc:
                self.handle_low_stock_alert(exc)
            self.pause()

    def action_stock(self, transaction_type: str) -> None:
        product_id = self.prompt_int("Product ID")

        if transaction_type == "ADJUSTMENT":
            new_qty = self.prompt_int("Set exact quantity to")
            product, txn = self.db.update_stock(
                product_id=product_id,
                quantity_change=new_qty,
                transaction_type="ADJUSTMENT",
                user_id=self.current_user_id,
                notes="Manual stock adjustment",
            )
        else:
            qty = self.prompt_int("Quantity")
            product, txn = self.db.update_stock(
                product_id=product_id,
                quantity_change=qty,
                transaction_type=transaction_type,
                user_id=self.current_user_id,
                notes=f"Manual stock {transaction_type}",
            )

        self.print_success(
            f"Stock updated for '{product.name}'. "
            f"New quantity: {product.quantity} "
            f"(change: {txn.quantity_change:+d})."
        )

    # ------------------------------------------------------------------
    # Analytics menus
    # ------------------------------------------------------------------

    def menu_reports(self) -> None:
        actions = {
            "1": ("Total inventory value", self.report_total_value),
            "2": ("Inventory value by category", self.report_value_by_category),
            "3": ("Low-stock items", self.report_low_stock),
            "4": ("Transaction history", self.report_transactions),
            "5": ("Top products by value", self.report_top_products),
            "6": ("Supplier stock summary", self.report_supplier_summary),
            "7": ("Back", None),
        }

        while True:
            self.clear_screen()
            print("=== Reports & Analytics ===")
            for key, (label, _) in actions.items():
                print(f"  {key}. {label}")

            choice = self.prompt("Choose an option")
            if choice == "7":
                return

            action = actions.get(choice, (None, None))[1]
            if action is None:
                print("Invalid choice.")
                self.pause()
                continue

            try:
                action()
            except DatabaseError as exc:
                self.print_error(exc)
            self.pause()

    def report_total_value(self) -> None:
        summary = self.db.get_total_inventory_value()
        print(
            tabulate(
                [
                    ["Products", summary["product_count"]],
                    ["Total Units", summary["total_units"]],
                    ["Total Inventory Value", f"${summary['total_value']:.2f}"],
                ],
                headers=["Metric", "Value"],
                tablefmt="grid",
            )
        )

    def report_value_by_category(self) -> None:
        rows = self.db.get_inventory_value_by_category()
        print(
            tabulate(
                [
                    [
                        r["category_name"],
                        r["product_count"],
                        r["total_units"],
                        f"${r['category_value']:.2f}",
                    ]
                    for r in rows
                ],
                headers=["Category", "Products", "Units", "Value"],
                tablefmt="grid",
            )
        )

    def report_low_stock(self) -> None:
        use_custom = self.prompt("Use custom threshold? (y/N)", default="N").lower()
        if use_custom == "y":
            threshold = self.prompt_int("Threshold quantity")
            products = self.db.get_low_stock_items(threshold=threshold)
        else:
            products = self.db.get_low_stock_items()

        self.display_products(products)
        if products:
            self.print_warning(f"{len(products)} item(s) need attention.")

    def report_transactions(self) -> None:
        filter_product = self.prompt("Filter by product ID (optional)", default="")
        limit = self.prompt_int("Number of records", default=20)

        product_id = int(filter_product) if filter_product else None
        transactions = self.db.get_transaction_history(
            product_id=product_id,
            limit=limit,
        )

        if not transactions:
            print("\nNo transactions found.")
            return

        print(
            tabulate(
                [
                    [
                        t.id,
                        t.created_at,
                        t.product_sku,
                        t.product_name,
                        t.transaction_type,
                        t.quantity_change,
                        t.quantity_before,
                        t.quantity_after,
                        t.username or "-",
                        t.notes or "-",
                    ]
                    for t in transactions
                ],
                headers=[
                    "ID",
                    "Date",
                    "SKU",
                    "Product",
                    "Type",
                    "Change",
                    "Before",
                    "After",
                    "User",
                    "Notes",
                ],
                tablefmt="grid",
            )
        )

    def report_top_products(self) -> None:
        limit = self.prompt_int("How many products", default=5)
        rows = self.db.get_top_products_by_value(limit=limit)
        print(
            tabulate(
                [
                    [
                        r["sku"],
                        r["name"],
                        r["category_name"],
                        r["quantity"],
                        f"${r['unit_price']:.2f}",
                        f"${r['line_value']:.2f}",
                    ]
                    for r in rows
                ],
                headers=["SKU", "Name", "Category", "Qty", "Unit Price", "Line Value"],
                tablefmt="grid",
            )
        )

    def report_supplier_summary(self) -> None:
        rows = self.db.get_supplier_stock_summary()
        print(
            tabulate(
                [
                    [
                        r["supplier_name"],
                        r["product_count"],
                        r["total_units"],
                        f"${r['stock_value']:.2f}",
                    ]
                    for r in rows
                ],
                headers=["Supplier", "Products", "Units", "Stock Value"],
                tablefmt="grid",
            )
        )

    # ------------------------------------------------------------------
    # Reference data menus
    # ------------------------------------------------------------------

    def menu_categories(self) -> None:
        while True:
            self.clear_screen()
            print("=== Category Management ===")
            print("  1. List categories")
            print("  2. Add category")
            print("  3. Update category")
            print("  4. Delete category")
            print("  5. Back")

            choice = self.prompt("Choose an option")
            try:
                if choice == "1":
                    categories = self.db.get_all_categories()
                    print(
                        tabulate(
                            [[c.id, c.name, c.description or "-"] for c in categories],
                            headers=["ID", "Name", "Description"],
                            tablefmt="grid",
                        )
                    )
                elif choice == "2":
                    name = self.prompt("Category name")
                    description = self.prompt("Description", default="")
                    category = self.db.create_category(name, description or None)
                    self.print_success(f"Category '{category.name}' created.")
                elif choice == "3":
                    category_id = self.prompt_int("Category ID")
                    name = self.prompt("New name")
                    description = self.prompt("New description", default="")
                    category = self.db.update_category(
                        category_id, name, description or None
                    )
                    self.print_success(f"Category '{category.name}' updated.")
                elif choice == "4":
                    category_id = self.prompt_int("Category ID")
                    self.db.delete_category(category_id)
                    self.print_success("Category deleted.")
                elif choice == "5":
                    return
                else:
                    print("Invalid choice.")
            except DatabaseError as exc:
                self.print_error(exc)
            self.pause()

    def menu_suppliers(self) -> None:
        while True:
            self.clear_screen()
            print("=== Supplier Management ===")
            print("  1. List suppliers")
            print("  2. Add supplier")
            print("  3. Delete supplier")
            print("  4. Back")

            choice = self.prompt("Choose an option")
            try:
                if choice == "1":
                    suppliers = self.db.get_all_suppliers()
                    print(
                        tabulate(
                            [
                                [s.id, s.name, s.contact_person or "-", s.email or "-", s.phone or "-"]
                                for s in suppliers
                            ],
                            headers=["ID", "Name", "Contact", "Email", "Phone"],
                            tablefmt="grid",
                        )
                    )
                elif choice == "2":
                    name = self.prompt("Supplier name")
                    contact = self.prompt("Contact person", default="")
                    email = self.prompt("Email", default="")
                    phone = self.prompt("Phone", default="")
                    address = self.prompt("Address", default="")
                    supplier = self.db.create_supplier(
                        name=name,
                        contact_person=contact or None,
                        email=email or None,
                        phone=phone or None,
                        address=address or None,
                    )
                    self.print_success(f"Supplier '{supplier.name}' created.")
                elif choice == "3":
                    supplier_id = self.prompt_int("Supplier ID")
                    self.db.delete_supplier(supplier_id)
                    self.print_success("Supplier deleted.")
                elif choice == "4":
                    return
                else:
                    print("Invalid choice.")
            except DatabaseError as exc:
                self.print_error(exc)
            self.pause()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        initialize_database(seed_sample_data=True)
        self.select_user()

        main_menu: dict[str, tuple[str, Optional[Callable[[], None]]]] = {
            "1": ("Product Management", self.menu_products),
            "2": ("Stock Operations", self.menu_stock),
            "3": ("Categories", self.menu_categories),
            "4": ("Suppliers", self.menu_suppliers),
            "5": ("Reports & Analytics", self.menu_reports),
            "6": ("Switch User", self.select_user),
            "7": ("Exit", None),
        }

        while True:
            self.clear_screen()
            print("=" * 48)
            print("   INVENTORY MANAGEMENT SYSTEM")
            print("=" * 48)
            for key, (label, _) in main_menu.items():
                print(f"  {key}. {label}")

            choice = self.prompt("Choose an option")
            if choice == "7":
                print("\nGoodbye!")
                sys.exit(0)

            action = main_menu.get(choice, (None, None))[1]
            if action is None:
                print("Invalid choice.")
                self.pause()
                continue

            action()
            self.pause()


def main() -> None:
    try:
        InventoryCLI().run()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
