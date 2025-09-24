from flask import Flask, jsonify
import sqlite3
import random

app = Flask(__name__)

DB_FILE = "prices.db"


# =======================
# Database Setup
# =======================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            brand TEXT,
            source TEXT,
            price REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# =======================
# Scraping Function
# =======================
def scrape_jumia(product_name):
    """
    Dummy scraper function – replace with real scraping logic later.
    For now, it returns a fake price for testing.
    """
    try:
        return round(random.uniform(1000, 5000), 2)
    except Exception as e:
        print(f"Scrape error for {product_name}: {e}")
        return None


# =======================
# Save Price to Database
# =======================
def save_price(product, brand, source, price):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO prices (product, brand, source, price) VALUES (?, ?, ?, ?)",
        (product, brand, source, price)
    )
    conn.commit()
    conn.close()


# =======================
# Aggregates (No pandas)
# =======================
def compute_aggregates():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT product, MIN(price), MAX(price), AVG(price) FROM prices GROUP BY product")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {"message": "No data yet"}

    result = {}
    for row in rows:
        product, min_p, max_p, avg_p = row
        result[product] = {
            "min_price": min_p,
            "max_price": max_p,
            "avg_price": round(avg_p, 2),
        }
    return result


# =======================
# Routes
# =======================
@app.route("/")
def home():
    return jsonify({"message": "Welcome to the Price Scraper API"})


@app.route("/run_scrape")
def run_scrape_endpoint():
    test_products = ["hammer", "cement", "drill machine"]
    results = []

    for prod in test_products:
        price = scrape_jumia(prod)
        if price:  # ✅ clean syntax
            save_price(prod, prod.title(), "Jumia", price)
            results.append({"product": prod, "price": price})

    return jsonify({"scraped": results})


@app.route("/api/aggregates")
def api_aggregates():
    return jsonify(compute_aggregates())


# =======================
# Main Entry
# =======================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
