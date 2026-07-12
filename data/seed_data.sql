-- ============================================================================
-- Inventory Management System — Seed Data
-- ============================================================================
-- Run after schema initialization (config.py / SCHEMA_SQL).
-- SQLite: PRAGMA foreign_keys = ON; is required before inserts.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- Clear existing data (child tables first)
DELETE FROM stock_transactions;
DELETE FROM products;
DELETE FROM suppliers;
DELETE FROM categories;
DELETE FROM users;

-- Reset auto-increment counters
DELETE FROM sqlite_sequence WHERE name IN (
    'users',
    'categories',
    'suppliers',
    'products',
    'stock_transactions'
);

-- ============================================================================
-- USERS
-- ============================================================================

INSERT INTO users (username, email, role) VALUES
    ('admin',   'admin@inventory.local',   'admin'),
    ('jsmith',  'jsmith@inventory.local',  'manager'),
    ('awhite',  'awhite@inventory.local', 'staff'),
    ('pkumar',  'pkumar@inventory.local',  'staff');

-- ============================================================================
-- CATEGORIES
-- ============================================================================

INSERT INTO categories (name, description) VALUES
    ('Electronics',     'Electronic devices and accessories'),
    ('Office Supplies', 'Stationery and office consumables'),
    ('Furniture',       'Desks, chairs, and storage furniture'),
    ('Hardware',        'Tools, fasteners, and maintenance supplies'),
    ('Packaging',       'Boxes, labels, and shipping materials');

-- ============================================================================
-- SUPPLIERS
-- ============================================================================

INSERT INTO suppliers (name, contact_person, email, phone, address) VALUES
    ('TechSource Ltd',  'Jane Doe',    'jane@techsource.com',  '555-0101', '12 Tech Park, Austin TX'),
    ('OfficeMax',       'John Roe',    'john@officemax.com',   '555-0202', '45 Supply Lane, Denver CO'),
    ('FurniCo',         'Mary Lane',   'mary@furnico.com',     '555-0303', '78 Warehouse Rd, Chicago IL'),
    ('BuildRight Inc',  'Sam Patel',   'sam@buildright.com',   '555-0404', '90 Industrial Blvd, Dallas TX'),
    ('PackPro',         'Lisa Chen',   'lisa@packpro.com',     '555-0505', '22 Logistics Way, Seattle WA');

-- ============================================================================
-- PRODUCTS
-- category_id: 1=Electronics, 2=Office, 3=Furniture, 4=Hardware, 5=Packaging
-- supplier_id: 1=TechSource, 2=OfficeMax, 3=FurniCo, 4=BuildRight, 5=PackPro
-- ============================================================================

INSERT INTO products
    (sku, name, description, category_id, supplier_id, unit_price, quantity, reorder_level)
VALUES
    -- Electronics (some intentionally low-stock)
    ('ELEC-001', 'Wireless Mouse',        'Ergonomic wireless mouse, 2.4 GHz',       1, 1,  24.99,  45, 10),
    ('ELEC-002', 'USB-C Hub',             '7-in-1 USB-C adapter',                    1, 1,  39.99,   8, 15),
    ('ELEC-003', 'Mechanical Keyboard',   'RGB mechanical keyboard, blue switches',  1, 1,  89.99,  22,  8),
    ('ELEC-004', '27" Monitor',           'IPS 1080p office monitor',                1, 1, 249.99,   6,  5),
    ('ELEC-005', 'Webcam HD',             '1080p USB webcam with microphone',        1, 1,  59.99,   3, 10),

    -- Office Supplies
    ('OFF-001',  'A4 Paper Ream',         '500 sheets, 80gsm white paper',           2, 2,   5.49, 120, 20),
    ('OFF-002',  'Ballpoint Pens (Box)',  'Box of 50 blue ballpoint pens',         2, 2,  12.00,   5, 10),
    ('OFF-003',  'Sticky Notes Pack',     '12 pads, 3x3 inch, assorted colors',    2, 2,   8.99,  35, 15),
    ('OFF-004',  'Stapler Heavy Duty',    'Metal stapler, 100-sheet capacity',     2, 2,  18.50,  14,  8),
    ('OFF-005',  'File Folders (Box)',    'Box of 100 manila file folders',        2, 2,  22.00,   2, 10),

    -- Furniture
    ('FURN-001', 'Office Chair',          'Adjustable mesh ergonomic chair',         3, 3, 199.99,  12,  5),
    ('FURN-002', 'Standing Desk',         'Electric height-adjustable desk',         3, 3, 449.99,   4,  3),
    ('FURN-003', 'Filing Cabinet',        '4-drawer metal filing cabinet',           3, 3, 159.99,   7,  4),
    ('FURN-004', 'Bookshelf Unit',        '5-tier open bookshelf, walnut finish',    3, 3,  89.99,  10,  5),

    -- Hardware
    ('HARD-001', 'Screwdriver Set',       '20-piece precision screwdriver set',      4, 4,  29.99,  18,  8),
    ('HARD-002', 'Cable Ties (Pack)',     'Pack of 200 nylon cable ties, 8 inch',    4, 4,   6.99,  50, 20),
    ('HARD-003', 'Wall Anchor Kit',       'Assorted drywall anchor kit, 100 pcs',    4, 4,  11.49,   1, 15),

    -- Packaging
    ('PACK-001', 'Shipping Box (Medium)', '18x12x10 corrugated shipping box',        5, 5,   2.49, 200, 50),
    ('PACK-002', 'Bubble Wrap Roll',      '12 inch x 50 ft bubble wrap roll',        5, 5,  14.99,  30, 10),
    ('PACK-003', 'Shipping Labels',       'Roll of 500 thermal shipping labels',     5, 5,  19.99,   0, 10);

-- ============================================================================
-- STOCK TRANSACTIONS (sample audit history)
-- user_id: 1=admin, 2=jsmith, 3=awhite
-- product_id matches insertion order above (1–20)
-- ============================================================================

INSERT INTO stock_transactions
    (product_id, user_id, transaction_type, quantity_change, quantity_before, quantity_after, notes)
VALUES
    -- Initial stock receipts
    (1,  1, 'IN',          50,  0, 50, 'Initial stock receipt — Wireless Mouse'),
    (2,  1, 'IN',          20,  0, 20, 'Initial stock receipt — USB-C Hub'),
    (3,  1, 'IN',          25,  0, 25, 'Initial stock receipt — Mechanical Keyboard'),
    (6,  2, 'IN',         150,  0, 150, 'Bulk order — A4 Paper Ream'),
    (11, 2, 'IN',          15,  0, 15, 'Initial stock receipt — Office Chair'),

    -- Sales / dispatches
    (1,  3, 'OUT',         -5, 50, 45, 'Dispatched to Sales Dept'),
    (2,  3, 'OUT',        -12, 20,  8, 'Dispatched to IT Dept — triggered low-stock alert'),
    (6,  3, 'OUT',        -30, 150, 120, 'Monthly office supply distribution'),
    (3,  3, 'OUT',         -3, 25, 22, 'Dispatched to Engineering team'),

    -- Stock adjustments
    (5,  2, 'ADJUSTMENT',   3,  5,  3, 'Physical count correction — Webcam HD'),
    (17, 2, 'ADJUSTMENT',   1,  5,  1, 'Physical count correction — Wall Anchor Kit'),
    (20, 1, 'ADJUSTMENT',   0,  2,  0, 'Stock depleted — Shipping Labels out of stock'),

    -- Recent restocking
    (4,  2, 'IN',           6,  0,  6, 'Restock order received — 27" Monitor'),
    (12, 2, 'IN',           4,  0,  4, 'Restock order received — Standing Desk'),
    (7,  3, 'OUT',          -7, 12,  5, 'Dispatched to Admin team — low stock warning'),
    (18, 1, 'IN',          50, 150, 200, 'Bulk restock — Shipping Boxes');

-- ============================================================================
-- Verification queries (optional — uncomment to inspect after seeding)
-- ============================================================================

-- SELECT COUNT(*) AS user_count         FROM users;
-- SELECT COUNT(*) AS category_count     FROM categories;
-- SELECT COUNT(*) AS supplier_count      FROM suppliers;
-- SELECT COUNT(*) AS product_count       FROM products;
-- SELECT COUNT(*) AS transaction_count   FROM stock_transactions;

-- SELECT
--     COUNT(p.id)                        AS product_count,
--     COALESCE(SUM(p.quantity), 0)       AS total_units,
--     COALESCE(SUM(p.quantity * p.unit_price), 0.0) AS total_inventory_value
-- FROM products p;

-- SELECT p.sku, p.name, p.quantity, p.reorder_level
-- FROM products p
-- WHERE p.quantity <= p.reorder_level
-- ORDER BY p.quantity ASC;
