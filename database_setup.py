import sqlite3
from faker import Faker
import random

# Initialize Faker
fake = Faker()

# Connect to SQLite database
conn = sqlite3.connect("retail_chatbot.db")
cursor = conn.cursor()

# Create Products Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL,
    description TEXT NOT NULL
)
""")

# Create Orders Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    product_id INTEGER NOT NULL,
    status TEXT CHECK( status IN ('Processing', 'Shipped', 'Delivered', 'Cancelled') ) NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products (id)
)
""")

# Tech product categories and sample names
categories = {
    "Phone": ["iPhone 15", "Samsung Galaxy S23", "Google Pixel 7", "OnePlus 11"],
    "Laptop": ["MacBook Air M2", "Dell XPS 15", "Lenovo ThinkPad X1", "ASUS ROG Strix"],
    "Tablet": ["iPad Pro", "Samsung Galaxy Tab S8", "Microsoft Surface Pro 9"],
    "Smartwatch": ["Apple Watch Series 8", "Samsung Galaxy Watch 5", "Garmin Fenix 7"],
    "Headphones": ["Sony WH-1000XM5", "Bose QC45", "AirPods Pro", "Sennheiser Momentum 4"],
    "Gaming Console": ["PlayStation 5", "Xbox Series X", "Nintendo Switch OLED"],
    "Smart Home": ["Amazon Echo", "Google Nest Hub", "Philips Hue Smart Bulb"],
    "Accessories": ["Logitech MX Master 3", "Anker Power Bank", "Razer Gaming Mouse"]
}

# Insert 50 fake products
products = []
for category, product_names in categories.items():
    for name in product_names:
        price = round(random.uniform(50, 2000), 2)  # Price range $50 - $2000
        stock = random.randint(0, 50)  # Random stock availability
        description = fake.sentence(nb_words=12)  # Fake description
        products.append((name, category, price, stock, description))

cursor.executemany("INSERT INTO products (name, category, price, stock, description) VALUES (?, ?, ?, ?, ?)", products)

# Insert 10 fake orders with product_id reference
orders = []
for _ in range(10):
    order_id = fake.uuid4()[:8]  # Short unique order ID
    product_id = random.randint(1, len(products))  # Pick a random product ID
    status = random.choice(["Processing", "Shipped", "Delivered", "Cancelled"])  # Random status
    orders.append((order_id, product_id, status))

cursor.executemany("INSERT INTO orders (order_id, product_id, status) VALUES (?, ?, ?)", orders)

# Commit and close connection
conn.commit()
conn.close()

print("Database setup complete. 50 products and 10 orders inserted!")
