"""Price Monitor - Prototype (Flask)

A lightweight web app to scrape retail prices, store them in SQLite (prototype),
and surface heuristics for fast-selling & high-demand items.
"""
from flask import Flask, jsonify, render_template_string, request
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime, timedelta
import csv
import os
import time
from rapidfuzz import process, fuzz

DB_FILE = 'prices_prototype.db'
SKU_CSV = 'sku_master.csv'

RETAILERS = [
    {"name":"Jumia", "search":"https://www.jumia.co.ke/catalog/?q={q}", "parser":"jumia"},
    {"name":"Carrefour", "search":"https://www.carrefour.ke/search?text={q}", "parser":"carrefour"},
    {"name":"Naivas", "search":"https://naivas.online/search?search={q}", "parser":"generic"},
    {"name":"Kilimall", "search":"https://www.kilimall.co.ke/search?q={q}", "parser":"generic"},
    {"name":"CrownPaints", "search":"https://www.crownpaints.co.ke/?s={q}", "parser":"generic"},
    {"name":"Ebuild", "search":"https://www.ebuild.ke/?s={q}", "parser":"generic"},
    {"name":"BuildersHome", "search":"https://thebuildershome.co.ke/?s={q}", "parser":"generic"},
    {"name":"ParklandsHardware", "search":"https://parklands-hardware.co.ke/?s={q}", "parser":"generic"},
    {"name":"NaneHardware", "search":"https://nanehomes.com/?s={q}", "parser":"generic"},
    {"name":"FastlaneHardware", "search":"https://fastlanehardware.co.ke/?s={q}", "parser":"generic"},
]

HEADERS = {'User-Agent':'Mozilla/5.0 (compatible; PriceMonitor/1.0; +https://example.com)'}

def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute('''
CREATE TABLE IF NOT EXISTS raw_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retailer TEXT,
    product_title TEXT,
    price_kes REAL,
    availability TEXT,
    scraped_at TEXT,
    product_url TEXT
)
''')
    cur.execute('''
CREATE TABLE IF NOT EXISTS sku_map (
    sku TEXT PRIMARY KEY,
    canonical_name TEXT
)
''')
    con.commit()
    con.close()

def generate_sku_template():
    if os.path.exists(SKU_CSV):
        return
    rows = [
        ('SKU001','Cement 50kg - Dangote'),
        ('SKU002','Cement 50kg - Twiga'),
        ('SKU003','White Emulsion Paint 5L - Crown'),
        ('SKU004','Cordless Drill - 18V'),
        ('SKU005','Hammer 1kg - Fiberglass handle'),
    ]
    with open(SKU_CSV,'w',newline='',encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['sku','canonical_name'])
        for r in rows:
            w.writerow(r)

def load_sku_master():
    if not os.path.exists(SKU_CSV):
        generate_sku_template()
    sku_map = {}
    with open(SKU_CSV,newline='',encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            sku_map[row['sku']] = row['canonical_name']
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    for sku, cname in sku_map.items():
        cur.execute('INSERT OR IGNORE INTO sku_map (sku, canonical_name) VALUES (?,?)', (sku, cname))
    con.commit()
    con.close()
    return sku_map

def parse_price(s: str):
    if not s: return None
    s2 = ''.join(ch for ch in s if ch.isdigit() or ch in '.').strip()
    try:
        return float(s2) if s2 else None
    except:
        return None

def parse_generic(html: str, base_url: str):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    cards = []
    for sel in ['.product', '.item', '.product-card', '.list-item', 'article']:
        cards = soup.select(sel)
        if cards:
            break
    if not cards:
        anchors = soup.select('a')[:120]
        for a in anchors:
            txt = a.get_text(' ',strip=True)
            parent = a.parent
            nearby = parent.get_text(' ',strip=True) if parent else txt
            if 'KSh' in nearby or 'KES' in nearby or any(ch.isdigit() for ch in nearby):
                price = parse_price(nearby)
                items.append({'title':txt[:120],'price_kes':price,'availability':'','url':requests.compat.urljoin(base_url, a.get('href') or '')})
        return items
    for c in cards[:80]:
        title = ''
        for tsel in ['h2','h3','.title','.name','.product-name']:
            el = c.select_one(tsel)
            if el:
                title = el.get_text(' ',strip=True)
                break
        if not title:
            title = c.get_text(' ',strip=True)[:120]
        price_text = ''
        for psel in ['.price', '.product-price', '.prc', '.amount']:
            pel = c.select_one(psel)
            if pel:
                price_text = pel.get_text(' ',strip=True)
                break
        price = parse_price(price_text)
        link_el = c.select_one('a')
        url = requests.compat.urljoin(base_url, link_el['href']) if link_el and link_el.get('href') else base_url
        items.append({'title':title,'price_kes':price,'availability':'','url':url})
    return items

def parse_jumia(html: str, base_url: str):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    cards = soup.select('article') or soup.select('.sku')
    for c in cards[:60]:
        title_el = c.select_one('h3') or c.select_one('.name')
        price_el = c.select_one('.prc') or c.select_one('.price')
        link_el = c.select_one('a')
        title = title_el.get_text(' ',strip=True) if title_el else c.get_text(' ',strip=True)[:120]
        price_text = price_el.get_text(' ',strip=True) if price_el else ''
        price = parse_price(price_text)
        url = requests.compat.urljoin(base_url, link_el['href']) if link_el and link_el.get('href') else base_url
        items.append({'title':title,'price_kes':price,'availability':'','url':url})
    return items

def parse_carrefour(html: str, base_url: str):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    cards = soup.select('.product-item') or soup.select('.product')
    for c in cards[:60]:
        title_el = c.select_one('.product-title') or c.select_one('h2')
        price_el = c.select_one('.sales-price') or c.select_one('.price')
        link_el = c.select_one('a')
        title = title_el.get_text(' ',strip=True) if title_el else c.get_text(' ',strip=True)[:120]
        price = parse_price(price_el.get_text(' ',strip=True)) if price_el else None
        url = requests.compat.urljoin(base_url, link_el['href']) if link_el and link_el.get('href') else base_url
        items.append({'title':title,'price_kes':price,'availability':'','url':url})
    return items

def search_and_parse(rcfg, query):
    url = rcfg['search'].format(q=requests.utils.requote_uri(query))
    try:
        r = requests.get(url, headers=HEADERS, timeout=18)
    except Exception as e:
        return []
    if r.status_code != 200:
        return []
    parser = rcfg.get('parser','generic')
    if parser == 'jumia':
        items = parse_jumia(r.text, url)
    elif parser == 'carrefour':
        items = parse_carrefour(r.text, url)
    else:
        items = parse_generic(r.text, url)
    for it in items:
        it['retailer'] = rcfg['name']
    return items

def save_raw_rows(rows):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    for r in rows:
        cur.execute('''INSERT INTO raw_prices (retailer, product_title, price_kes, availability, scraped_at, product_url)
                       VALUES (?,?,?,?,?,?)''', (
            r.get('retailer'), r.get('title'), r.get('price_kes'), r.get('availability',''), datetime.utcnow().isoformat(), r.get('url')
        ))
    con.commit()
    con.close()

def map_title_to_sku(title, sku_master_names):
    best = process.extractOne(title, sku_master_names, scorer=fuzz.token_sort_ratio)
    if best:
        return best[0], best[1]
    return None, 0

def compute_aggregates(days=30):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cutoff = datetime.utcnow() - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()
    cur.execute('SELECT sku, canonical_name FROM sku_map')
    sku_rows = cur.fetchall()
    sku_map = {sku: cname for sku, cname in sku_rows}
    canonical_names = list(sku_map.values())
    cur.execute('SELECT retailer, product_title, price_kes, availability, scraped_at FROM raw_prices WHERE scraped_at >= ?', (cutoff_iso,))
    raw = cur.fetchall()
    con.close()
    grouped = {}
    for retailer, ptitle, price, availability, scraped_at in raw:
        if not price:
            continue
        best_name, score = map_title_to_sku(ptitle, canonical_names)
        if score < 70:
            key = ('__UNKNOWN__', ptitle)
        else:
            key = (best_name,)
        entry = grouped.get(key, [])
        entry.append({'retailer':retailer,'title':ptitle,'price':price,'availability':availability,'scraped_at':scraped_at})
        grouped[key] = entry
    results = []
    for key, items in grouped.items():
        if key[0] == '__UNKNOWN__':
            name = key[1]
        else:
            name = key[0]
        prices = [it['price'] for it in items if it['price'] is not None]
        n_listings = len(prices)
        if n_listings == 0:
            continue
        avg_price = sum(prices)/n_listings
        min_price = min(prices)
        max_price = max(prices)
        volatility = (max_price - min_price)/avg_price if avg_price else 0
        stockouts = sum(1 for it in items if 'out' in (it['availability'] or '').lower() or 'sold' in (it['availability'] or '').lower())
        stockout_frac = stockouts / n_listings
        listing_count_score = min(n_listings/20, 1.0)
        volatility_score = min(volatility / 0.2, 1.0)
        stockout_score = stockout_frac
        fast_selling_score = 0.45*listing_count_score + 0.35*stockout_score + 0.2*volatility_score
        high_demand_score = 0.6*listing_count_score + 0.4*volatility_score
        results.append({
            'name': name,
            'n_listings': n_listings,
            'avg_price': round(avg_price,2),
            'min_price': round(min_price,2),
            'max_price': round(max_price,2),
            'volatility': round(volatility,3),
            'stockout_frac': round(stockout_frac,3),
            'fast_selling_score': round(fast_selling_score,3),
            'high_demand_score': round(high_demand_score,3)
        })
    results_sorted = sorted(results, key=lambda x: x['fast_selling_score'], reverse=True)
    return results_sorted

app = Flask(__name__)

INDEX_HTML = '''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Price Monitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body class="bg-light">
    <div class="container py-4">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Price Monitor (Prototype)</h3>
        <div>
          <a class="btn btn-sm btn-primary" href="/run_scrape">Run one-time scrape</a>
          <a class="btn btn-sm btn-secondary" href="/api/aggregates">API: Aggregates</a>
        </div>
      </div>
      <p>Top items by fast-selling score. Edit sku_master.csv to map your SKUs.</p>
      <div id="table-area"></div>
    </div>
    <script>
    async function loadData(){
      const res = await fetch('/api/aggregates');
      const data = await res.json();
      const area = document.getElementById('table-area');
      if(!data.length){ area.innerHTML = '<div class="alert alert-info">No data yet. Run a scrape.</div>'; return; }
      let html = '<table class="table table-sm table-striped"><thead><tr><th>#</th><th>Item</th><th>Listings</th><th>Avg KES</th><th>Min</th><th>Max</th><th>FastSell</th><th>HighDemand</th></tr></thead><tbody>';
      data.slice(0,100).forEach((r,i)=>{
        html += `<tr><td>${i+1}</td><td>${r.name}</td><td>${r.n_listings}</td><td>${r.avg_price}</td><td>${r.min_price}</td><td>${r.max_price}</td><td>${r.fast_selling_score}</td><td>${r.high_demand_score}</td></tr>`;
      });
      html += '</tbody></table>';
      area.innerHTML = html;
    }
    loadData();
    </script>
  </body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/run_scrape')
def run_scrape_endpoint():
    sku_map = load_sku_master()
    queries = list(sku_map.values())[:12]
    total = 0
    for q in queries:
        for rcfg in RETAILERS:
            try:
                items = search_and_parse(rcfg, q)
                if items:
                    save_raw_rows(items)
                    total += len(items)
                time.sleep(0.8)
            except Exception as e:
                print('Scrape error', e)
    return f"Scrape complete. Saved ~{total} rows. <a href='/'>Back</a>"

@app.route('/api/aggregates')
def api_aggregates():
    days = int(request.args.get('days', '30'))
    agg = compute_aggregates(days=days)
    return jsonify(agg)

@app.route('/api/fast_selling')
def api_fast_selling():
    days = int(request.args.get('days', '14'))
    agg = compute_aggregates(days=days)
    return jsonify(agg[:30])

if __name__ == '__main__':
    init_db()
    load_sku_master()
    print('DB initialized at', DB_FILE)
    app.run(host='0.0.0.0', port=5000, debug=True)
