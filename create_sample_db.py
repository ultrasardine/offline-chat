#!/usr/bin/env python3
"""
Create a sample SQLite database with company sales data for testing.

This script creates a database with:
- Customers
- Products
- Sales representatives
- Orders
- Order items
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Sample data
CUSTOMERS = [
    ("Acme Corp", "John Smith", "john@acme.com", "555-0101", "123 Business St, New York, NY"),
    ("TechStart Inc", "Sarah Johnson", "sarah@techstart.com", "555-0102", "456 Innovation Ave, San Francisco, CA"),
    ("Global Solutions", "Mike Chen", "mike@globalsolutions.com", "555-0103", "789 Enterprise Blvd, Chicago, IL"),
    ("DataFlow Systems", "Emily Brown", "emily@dataflow.com", "555-0104", "321 Tech Park, Austin, TX"),
    ("CloudNine Ltd", "David Wilson", "david@cloudnine.com", "555-0105", "654 Cloud Way, Seattle, WA"),
    ("Innovate Co", "Lisa Anderson", "lisa@innovate.com", "555-0106", "987 Startup Lane, Boston, MA"),
    ("MegaTech Industries", "Robert Taylor", "robert@megatech.com", "555-0107", "147 Industrial Dr, Detroit, MI"),
    ("SmartBiz LLC", "Jennifer Martinez", "jennifer@smartbiz.com", "555-0108", "258 Commerce St, Miami, FL"),
    ("FutureSoft", "William Garcia", "william@futuresoft.com", "555-0109", "369 Software Pkwy, Denver, CO"),
    ("Quantum Enterprises", "Maria Rodriguez", "maria@quantum.com", "555-0110", "741 Quantum Rd, Portland, OR"),
]

PRODUCTS = [
    ("Enterprise Software License", "Software", 5000.00, 50),
    ("Cloud Storage - 1TB", "Service", 120.00, 200),
    ("Professional Consulting - Hour", "Service", 150.00, 1000),
    ("Hardware Server", "Hardware", 3500.00, 25),
    ("Network Router", "Hardware", 800.00, 40),
    ("Security Suite Annual", "Software", 2400.00, 100),
    ("Database License", "Software", 4200.00, 30),
    ("Support Contract - Premium", "Service", 1800.00, 75),
    ("Training Package", "Service", 950.00, 60),
    ("Mobile App License", "Software", 299.00, 150),
]

SALES_REPS = [
    ("Alice Cooper", "alice.cooper@company.com", "555-1001", "2020-01-15"),
    ("Bob Martinez", "bob.martinez@company.com", "555-1002", "2019-06-20"),
    ("Carol White", "carol.white@company.com", "555-1003", "2021-03-10"),
    ("Dan Brown", "dan.brown@company.com", "555-1004", "2018-11-05"),
    ("Eve Davis", "eve.davis@company.com", "555-1005", "2022-02-28"),
]


def create_database(db_path: str = "sample_company.db"):
    """Create and populate the sample database."""

    # Remove existing database
    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()
        print(f"Removed existing database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    print("Creating tables...")

    cursor.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            stock_quantity INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE sales_reps (
            rep_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rep_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            hire_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            rep_id INTEGER NOT NULL,
            order_date DATE NOT NULL,
            status TEXT NOT NULL,
            total_amount DECIMAL(10, 2),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (rep_id) REFERENCES sales_reps(rep_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            subtotal DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # Insert customers
    print("Inserting customers...")
    for customer in CUSTOMERS:
        cursor.execute(
            "INSERT INTO customers (company_name, contact_name, email, phone, address) VALUES (?, ?, ?, ?, ?)", customer
        )

    # Insert products
    print("Inserting products...")
    for product in PRODUCTS:
        cursor.execute(
            "INSERT INTO products (product_name, category, unit_price, stock_quantity) VALUES (?, ?, ?, ?)", product
        )

    # Insert sales reps
    print("Inserting sales representatives...")
    for rep in SALES_REPS:
        cursor.execute("INSERT INTO sales_reps (rep_name, email, phone, hire_date) VALUES (?, ?, ?, ?)", rep)

    # Generate orders (last 6 months)
    print("Generating orders...")
    statuses = ["Completed", "Completed", "Completed", "Pending", "Shipped"]
    start_date = datetime.now() - timedelta(days=180)

    order_count = 0
    for _ in range(50):  # Generate 50 orders
        customer_id = random.randint(1, len(CUSTOMERS))
        rep_id = random.randint(1, len(SALES_REPS))
        order_date = start_date + timedelta(days=random.randint(0, 180))
        status = random.choice(statuses)

        cursor.execute(
            "INSERT INTO orders (customer_id, rep_id, order_date, status, total_amount) VALUES (?, ?, ?, ?, ?)",
            (customer_id, rep_id, order_date.strftime("%Y-%m-%d"), status, 0),
        )
        order_id = cursor.lastrowid
        order_count += 1

        # Add 1-4 items per order
        num_items = random.randint(1, 4)
        total_amount = 0

        for _ in range(num_items):
            product_id = random.randint(1, len(PRODUCTS))
            quantity = random.randint(1, 5)

            # Get product price
            cursor.execute("SELECT unit_price FROM products WHERE product_id = ?", (product_id,))
            unit_price = cursor.fetchone()[0]
            subtotal = unit_price * quantity
            total_amount += subtotal

            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
                (order_id, product_id, quantity, unit_price, subtotal),
            )

        # Update order total
        cursor.execute("UPDATE orders SET total_amount = ? WHERE order_id = ?", (total_amount, order_id))

    conn.commit()

    # Print summary
    print(f"\n{'=' * 60}")
    print("Database created successfully!")
    print(f"{'=' * 60}")
    print(f"Location: {db_path}")
    print("\nTables created:")
    print(f"  - customers: {len(CUSTOMERS)} records")
    print(f"  - products: {len(PRODUCTS)} records")
    print(f"  - sales_reps: {len(SALES_REPS)} records")
    print(f"  - orders: {order_count} records")

    cursor.execute("SELECT COUNT(*) FROM order_items")
    item_count = cursor.fetchone()[0]
    print(f"  - order_items: {item_count} records")

    # Show some sample queries
    print(f"\n{'=' * 60}")
    print("Sample queries you can try:")
    print(f"{'=' * 60}")

    print("\n1. Total sales by month:")
    cursor.execute("""
        SELECT strftime('%Y-%m', order_date) as month,
               COUNT(*) as order_count,
               SUM(total_amount) as total_sales
        FROM orders
        WHERE status = 'Completed'
        GROUP BY month
        ORDER BY month DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} orders, ${row[2]:,.2f}")

    print("\n2. Top 5 customers by revenue:")
    cursor.execute("""
        SELECT c.company_name,
               COUNT(o.order_id) as order_count,
               SUM(o.total_amount) as total_spent
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.status = 'Completed'
        GROUP BY c.customer_id
        ORDER BY total_spent DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} orders, ${row[2]:,.2f}")

    print("\n3. Top selling products:")
    cursor.execute("""
        SELECT p.product_name,
               SUM(oi.quantity) as units_sold,
               SUM(oi.subtotal) as revenue
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.status = 'Completed'
        GROUP BY p.product_id
        ORDER BY revenue DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} units, ${row[2]:,.2f}")

    print(f"\n{'=' * 60}")
    print("Ready to use with your agent!")
    print(f"{'=' * 60}\n")

    conn.close()


if __name__ == "__main__":
    create_database()
