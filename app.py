import sqlite3
import datetime
import requests
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
DB_FILE = "prices.db"

# -----------------------------
# Database Setup
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sku_map (
            sku TEXT PRIMARY KEY,
            canonical_name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            retailer TEXT,
            price REAL,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Dummy Scraper (replace later)
# -----------------------------
def scrape_dummy():
    """Example scraper, replace with real scraping logic."""
    data = [
        ("hammer-001", "Hammer", "RetailerA", 500),
        ("hammer-001", "Hammer", "RetailerB", 520),
        ("drill-002", "Drill", "RetailerA", 3500),
        ("drill-002", "Drill", "RetailerC", 3400),
    ]
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    for sku, cname, retailer, price in data:
        cur.execute("INSERT OR IGNORE INTO sku_map (sku, canonical_name) VALUES (?,?)", (sku, cname))
        cur.execute(
            "INSERT INTO prices (sku, retai
