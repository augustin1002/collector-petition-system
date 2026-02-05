import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS petitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT NOT NULL,
    place TEXT NOT NULL,
    department TEXT NOT NULL,
    problem TEXT NOT NULL,
    status TEXT NOT NULL
)
""")

conn.commit()
conn.close()
print("Database created successfully")
