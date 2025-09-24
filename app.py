def init_db():
    conn = sqlite3.connect("prices.db")
    cur = conn.cursor()
    # create sku_map table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sku_map (
            sku TEXT PRIMARY KEY,
            canonical_name TEXT
        )
    ''')
    # create prices table
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
