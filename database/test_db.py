import sqlite3

conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cur.fetchall())

# View variant_details
cur.execute("SELECT * FROM variant_details LIMIT 5")
for row in cur.fetchall():
    print(row)

conn.close()