"""SQLite storage for the shop app.

Plain functions, parameterized queries, no ORM. Four tables:
  products    - what the shop sells
  sales       - one row per completed checkout
  sale_items  - the items inside each sale (name and price are frozen
                snapshots, so old receipts stay correct even if the
                product is renamed or repriced later)
  audit_log   - who did what and when, at critical points only
"""

import os
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "shop.db")


def get_connection():
    """Open the database, creating the data folder if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


def now_string():
    """Current time as a string the database can store and sort."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    """Create the tables if they do not exist yet."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS products (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT NOT NULL,
               barcode TEXT UNIQUE NOT NULL,
               category TEXT NOT NULL,
               price REAL NOT NULL,
               cost REAL NOT NULL DEFAULT 0,
               stock INTEGER NOT NULL DEFAULT 0,
               brand TEXT DEFAULT '',
               unit TEXT DEFAULT 'Piece',
               image TEXT DEFAULT '')"""
    )
    # Migration for databases created before the image column existed.
    # Adding a column that is already there raises an error, which we
    # safely ignore.
    try:
        cur.execute("ALTER TABLE products ADD COLUMN image TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already there, nothing to do
    cur.execute(
        """CREATE TABLE IF NOT EXISTS sales (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               date TEXT NOT NULL,
               subtotal REAL NOT NULL,
               total REAL NOT NULL,
               payment TEXT NOT NULL,
               paid REAL NOT NULL,
               change REAL NOT NULL DEFAULT 0,
               cashier TEXT NOT NULL,
               customer_name TEXT DEFAULT '')"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS sale_items (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               sale_id INTEGER NOT NULL REFERENCES sales(id),
               product_id INTEGER NOT NULL,
               name TEXT NOT NULL,
               price REAL NOT NULL,
               quantity INTEGER NOT NULL)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS audit_log (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               date TEXT NOT NULL,
               user TEXT NOT NULL,
               action TEXT NOT NULL,
               details TEXT DEFAULT '')"""
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------ products ---

def add_product(name, barcode, category, price, cost=0, stock=0, brand="", unit="Piece", image=""):
    """Insert a product. Values must already be validated and cleaned."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products (name, barcode, category, price, cost, stock, brand, unit, image)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, barcode, category, price, cost, stock, brand, unit, image),
    )
    product_id = cur.lastrowid
    conn.commit()
    conn.close()
    return product_id


def get_product(product_id):
    """Fetch one product as a dict, or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_product_by_barcode(barcode):
    """Fetch one product by its exact barcode, or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE barcode = ?", (barcode,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def list_products():
    """All products, alphabetically. Pages do their own filtering."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def list_categories():
    """Every category currently in use, for the filter dropdowns."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM products ORDER BY category")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def update_product(product_id, name, barcode, category, price, cost, stock, brand, unit, image=""):
    """Overwrite a product's fields. Values must already be validated."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE products
           SET name = ?, barcode = ?, category = ?, price = ?,
               cost = ?, stock = ?, brand = ?, unit = ?, image = ?
           WHERE id = ?""",
        (name, barcode, category, price, cost, stock, brand, unit, image, product_id),
    )
    conn.commit()
    conn.close()


def delete_product(product_id):
    """Permanently delete a product. Past sales keep their own snapshots."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


def set_stock(product_id, new_stock):
    """Set a product's stock to an exact number."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
    conn.commit()
    conn.close()


def count_products():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM products")
    n = cur.fetchone()[0]
    conn.close()
    return n


def out_of_stock_products():
    """Products with zero stock, for the Home screen warning list."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE stock = 0 ORDER BY name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# --------------------------------------------------------------- sales ---

def record_sale(items, payment, paid, change, cashier, customer_name=""):
    """Write a sale, its items, and deduct stock, all in one transaction.

    items: list of dicts with product_id, name, price, quantity.
    The name and price are frozen snapshots: if the product is renamed
    or repriced later, this receipt still shows what was actually sold.
    Returns the new sale id.
    """
    subtotal = sum(i["price"] * i["quantity"] for i in items)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO sales (date, subtotal, total, payment, paid, change,
                                  cashier, customer_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (now_string(), subtotal, subtotal, payment, paid, change,
             cashier, customer_name),
        )
        sale_id = cur.lastrowid
        for i in items:
            cur.execute(
                """INSERT INTO sale_items (sale_id, product_id, name, price, quantity)
                   VALUES (?, ?, ?, ?, ?)""",
                (sale_id, i["product_id"], i["name"], i["price"], i["quantity"]),
            )
            # Deduct what was just sold, so stock is always truthful.
            cur.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (i["quantity"], i["product_id"]),
            )
        conn.commit()
    except Exception:
        # If anything fails halfway, undo everything: a sale must never
        # exist without its items, or stock without its sale.
        conn.rollback()
        raise
    finally:
        conn.close()
    return sale_id


def get_sale(sale_id):
    """One sale with its items attached, or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    sale = dict(row)
    cur.execute("SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id", (sale_id,))
    sale["items"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return sale


def list_sales(limit=100):
    """Sales newest first."""
    return list_sales_filtered("all", limit)


def _period_range(period):
    """(start, end) date strings for a named filter, end exclusive.

    Periods: 'today', 'yesterday', 'week' (last 7 days),
    'month' (last 30 days), 'all'. Dates are stored as
    'YYYY-MM-DD HH:MM:SS' text, so plain string comparison works.
    """
    today = datetime.now().date()
    day = today.strftime("%Y-%m-%d")
    if period == "today":
        return day, None
    if period == "yesterday":
        yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        return yesterday, day
    if period == "week":
        return (today - timedelta(days=6)).strftime("%Y-%m-%d"), None
    if period == "month":
        return (today - timedelta(days=29)).strftime("%Y-%m-%d"), None
    return None, None  # 'all': no bounds


def _filtered_query(table, period, limit):
    """Build a SELECT with an optional date range. Shared by the
    sales and audit listings so the filter logic lives in one place."""
    start, end = _period_range(period)
    query = "SELECT * FROM %s" % table
    params = []
    conditions = []
    if start:
        conditions.append("date >= ?")
        params.append(start)
    if end:
        conditions.append("date < ?")
        params.append(end)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return query, params


def list_sales_filtered(period="all", limit=500):
    """Sales newest first, optionally limited to a date period."""
    conn = get_connection()
    cur = conn.cursor()
    query, params = _filtered_query("sales", period, limit)
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def today_summary():
    """How many sales and how much revenue happened today."""
    conn = get_connection()
    cur = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM sales WHERE date LIKE ?",
        (today + "%",),
    )
    count, revenue = cur.fetchone()
    conn.close()
    return {"count": count, "revenue": revenue}


# ----------------------------------------------------------- audit log ---

def log_action(user, action, details=""):
    """Append one line to the audit log. Called at critical points only:
    product added, product edited, product deleted, stock adjusted,
    sale completed. The log is append-only; entries are never edited."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_log (date, user, action, details) VALUES (?, ?, ?, ?)",
        (now_string(), user, action, details),
    )
    conn.commit()
    conn.close()


def list_audit(limit=200):
    """Audit entries, newest first."""
    return list_audit_filtered(period="all", limit=limit)


def list_audit_filtered(period="all", action="all", query="", limit=500):
    """Audit entries newest first: date period, action type, and a
    free-text search (matches user, action, and details)."""
    start, end = _period_range(period)
    conditions = []
    params = []
    if start:
        conditions.append("date >= ?")
        params.append(start)
    if end:
        conditions.append("date < ?")
        params.append(end)
    if action != "all":
        conditions.append("action = ?")
        params.append(action)
    if query.strip():
        like = "%" + query.strip() + "%"
        conditions.append("(user LIKE ? OR action LIKE ? OR details LIKE ?)")
        params.extend([like, like, like])
    sql = "SELECT * FROM audit_log"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def list_audit_actions():
    """Every action type ever logged, for the audit filter dropdown."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT action FROM audit_log ORDER BY action")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


# ---------------------------------------------------------- seed data ---

SEED_PRODUCTS = [
    # name, barcode, category, price, cost, stock, brand, image file
    ("Coca-Cola 50cl", "5449000000996", "Beverages", 550, 400, 24, "Coca-Cola", "coke.jpg"),
    ("Pepsi 50cl", "5449000001234", "Beverages", 550, 400, 18, "Pepsi", "pepsi.jpg"),
    ("Fanta 50cl", "5449000005678", "Beverages", 550, 400, 20, "Fanta", "fanta.jpg"),
    ("Sprite 50cl", "5449000005679", "Beverages", 550, 400, 3, "Sprite", "sprite.jpg"),
    ("Peak Milk 400g", "6151100070041", "Groceries", 2800, 2500, 8, "Peak", "peak.jpg"),
    ("Indomie Chicken", "8964000100001", "Groceries", 300, 220, 45, "Indomie", "indomie.jpg"),
    ("Golden Morn 500g", "6154000011123", "Groceries", 1200, 900, 12, "Nestle", "golden.jpg"),
    ("Milo 200g", "6151000020045", "Groceries", 1500, 1150, 10, "Nestle", "milo.jpg"),
    ("Dettol Soap", "6192341100876", "Personal Care", 600, 450, 22, "Dettol", "dettol.jpg"),
    ("Closeup 120g", "6156000043210", "Personal Care", 850, 650, 9, "Closeup", "closeup.jpg"),
    ("Bread Loaf", "6157000054321", "Snacks", 700, 500, 14, "Fresh Bake", "bread.jpg"),
    ("Maggi Cubes", "6161000065432", "Groceries", 350, 250, 38, "Maggi", "maggi.jpg"),
]


def _seed_sale(product_quantities, payment, paid_extra, cashier, hours_ago, customer=""):
    """Record one sample sale dated a given number of hours in the past.

    Goes through the same record_sale path as a real checkout, so stock
    is deducted exactly like a real sale would deduct it."""
    items = []
    for barcode, qty in product_quantities:
        p = get_product_by_barcode(barcode)
        items.append({"product_id": p["id"], "name": p["name"],
                      "price": p["price"], "quantity": qty})
    total = sum(i["price"] * i["quantity"] for i in items)
    paid = total + paid_extra
    change = paid - total
    date = (datetime.now() - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO sales (date, subtotal, total, payment, paid, change,
                              cashier, customer_name)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (date, total, total, payment, paid, change, cashier, customer),
    )
    sale_id = cur.lastrowid
    for i in items:
        cur.execute(
            "INSERT INTO sale_items (sale_id, product_id, name, price, quantity)"
            " VALUES (?, ?, ?, ?, ?)",
            (sale_id, i["product_id"], i["name"], i["price"], i["quantity"]),
        )
        cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?",
                    (i["quantity"], i["product_id"]))
    cur.execute(
        "INSERT INTO audit_log (date, user, action, details) VALUES (?, ?, ?, ?)",
        (date, cashier, "Sale Completed",
         "Receipt #%06d | %d items | sample data" % (sale_id, len(items))),
    )
    conn.commit()
    conn.close()
    return sale_id


def seed_if_empty():
    """Fill a fresh database with sample products and recent sample sales.

    Runs only when the products table is empty, so real data is never
    overwritten. Sample sale dates are relative to right now, so the
    dashboard never looks stale."""
    if count_products() > 0:
        return
    for name, barcode, category, price, cost, stock, brand, image in SEED_PRODUCTS:
        add_product(name, barcode, category, price, cost, stock, brand, image=image)
    # (barcode, quantity) pairs, payment method, extra paid, cashier, hours ago
    samples = [
        ([("5449000000996", 2), ("8964000100001", 3)], "Cash", 100, "Cashier 1", 2),
        ([("6151100070041", 1), ("6151000020045", 2)], "Transfer", 0, "Admin", 5),
        ([("5449000001234", 4), ("6161000065432", 2)], "Cash", 200, "Cashier 1", 26),
        ([("6157000054321", 2), ("5449000005678", 2)], "Transfer", 0, "Admin", 30),
        ([("6192341100876", 1), ("6156000043210", 1)], "Cash", 50, "Cashier 2", 50),
        ([("5449000005679", 3), ("6154000011123", 1)], "Cash", 0, "Cashier 1", 74),
    ]
    for items, payment, extra, cashier, hours in samples:
        _seed_sale(items, payment, extra, cashier, hours)
    log_action("Admin", "Database Seeded", "Sample products and sales created")
