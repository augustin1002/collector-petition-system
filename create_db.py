import sqlite3

# Connect to database (creates file if not exists)
conn = sqlite3.connect("database.db")
cur = conn.cursor()

# Drop old table (optional but useful if structure changed)
cur.execute("DROP TABLE IF EXISTS petitions")

# Create new petitions table
cur.execute("""
CREATE TABLE petitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT NOT NULL,
    place TEXT NOT NULL,
    department TEXT NOT NULL,
    problem TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("✅ Petition database created successfully")
