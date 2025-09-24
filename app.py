import sqlite3
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string

# =======================
# Database Setup
# =======================
def init_db():
    conn = sqlite3.connect("prices.db")
    cur = conn.cursor()
    # SKU mapping table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sku_map (
            sku TEXT PRIMARY KEY,
            canonical_name TEXT
        )
    ''')
    # Prices table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            canonical_name TEXT,
            source TEXT,
            price REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


# =======================
# Flask App
# =======================
app = Flask(__name__)
init_db()   # ✅ make sure DB is ready


# =======================
# Helpers
# =======================
def save_price(sku, canonical_name, source, price):
    conn = sqlite3.connect("prices.db")
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO prices (sku, canonical_name, source, price)
        VALUES (?, ?, ?, ?)
    ''', (sku, canonical_name, source, price))
    conn.commit()
    conn.close()


def scrape_jumia(product_name):
    """Simple scraper for Jumia search results"""
    url = f"https://www.jumia.co.ke/catalog/?q={product_name.replace(' ', '+')}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    price_tag = soup.select_one("div.prc")
    if price_tag:
        price_text = price_tag.get_text().replace("KSh", "").replace(",", "").strip()
        try:
            return float(price_text)
        except:
            return None
    return None


def compute_aggregates(days=7):
    conn = sqlite3.connect("prices.db")
    cur = conn.cursor()
    cur.execute('''
        SELECT canonical_name, source, AVG(price), COUNT(*)
        FROM prices
        WHERE timestamp >= datetime('now', ?)
        GROUP BY canonical_name, source
    ''', (f'-{days} days',))
    rows = cur.fetchall()
    conn.close()
    return [
        {"product": r[0], "source": r[1], "avg_price": r[2], "samples": r[3]}
        for r in rows
    ]


# =======================
# Routes
# =======================
@app.route("/")
def home():
    return render_template_string("""
    <h2>🛠 Kenya Hardware Price Monitor</h2>
    <p><a href='/run_scrape'>Run Scraper</a></p>
    <p><a href='/api/aggregates'>View Aggregates (JSON)</a></p>
    """)


@app.route("/run_scrape")
def run_scrape_endpoint():
    test_products = ["hammer", "cement", "drill machine"]
    results = []
    for prod in test_products:
        price = scrape_jumia(prod)
        if
