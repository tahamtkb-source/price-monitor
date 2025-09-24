from flask import Flask, render_template_string, request, send_file
import sqlite3
import csv
import os
from datetime import datetime

app = Flask(__name__)

DB_FILE = "prices.db"

# ---------------------------
# Database setup
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            retailer TEXT,
            price REAL,
            date TEXT
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

# ---------------------------
# Fake scraper (replace later with real scraping logic)
# ---------------------------
def run_scraper():
    # Example data
    scraped_data = [
        ("SKU123", "RetailerA", 199.99, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("SKU456", "RetailerB", 299.50, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for sku, retailer, price, date in scraped_data:
        cursor.execute(
            """
            INSERT INTO prices (sku, retailer, price, date)
            VALUES (?, ?, ?, ?)
            """,
            (sku, retailer, price, date),
        )
    conn.commit()
    conn.close()

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def home():
    return render_template_string(
        """
        <h2>Price Monitor</h2>
        <form action="/run_scrape" method="post">
            <button type="submit">Run Scraper</button>
        </form>
        <br>
        <a href="/view_prices">View Saved Prices</a><br>
        <a href="/download_csv">Download CSV</a>
        """
    )

@app.route("/run_scrape", methods=["POST"])
def run_scrape():
    run_scraper()
    return "<p>Scraping complete! <a href='/'>Go back</a></p>"

@app.route("/view_prices")
def view_prices():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT sku, retailer, price, date FROM prices ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    html = "<h2>Saved Prices</h2><table border=1><tr><th>SKU</th><th>Retailer</th><th>Price</th><th>Date</th></tr>"
    for row in rows:
        html += "<tr>" + "".join([f"<td>{col}</td>" for col in row]) + "</tr>"
    html += "</table><br><a href='/'>Go Home</a>"

    return html

@app.route("/download_csv")
def download_csv():
    csv_file = "prices.csv"
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT sku, retailer, price, date FROM prices ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU", "Retailer", "Price", "Date"])
        writer.writerows(rows)

    return send_file(csv_file, as_attachment=True)

# ---------------------------
# Run app
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
