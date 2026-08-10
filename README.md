# Inventory Management System

A complete, end-to-end inventory management application built in **Python** with **SQLite**.  
Manage products, track stock movements, run analytics, and receive low-stock alert — all from a clean command-line interface.

---

## Features

| Feature | Description |
|---------|-------------|
| **Relational database** | 5 tables with primary/foreign keys and referential integrity |
| **Product CRUD** | Create, read, update, and delete products |
| **Stock tracking** | Stock IN, OUT, and ADJUSTMENT operations |
| **Automatic audit log** | Every stock change is recorded in `stock_transactions` |
| **Low-stock alerts** | Warnings when quantity drops to or below reorder level |
| **Analytics** | Inventory value, category breakdown, supplier summary, top products |
| **CLI interface** | Menu-driven terminal UI with formatted tables |

---

## Requirements

- Python 3.9+
- `tabulate` (listed in `requirements.txt`)

---

## Installation

```bash
# Clone or copy the project files into a directory
cd inventory-management

# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

--

## 🚀 Application Demo & Results

Here is a look at the interactive command-line interface and reporting system in action:

### 1. User Authentication & Main Dashboard
![Main Menu](results/demo1.png.png)

### 2. Total Inventory Value Report
![Inventory Value](results/demo2.png.png)

### 3. Custom Low-Stock Threshold Alerts
![Low Stock Alerts](results/demo3.png.png)

### 4. Supplier Stock Summary
![Supplier Summary](results/demo4.png.png)

--
