import sqlite3

conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()

# Remove all rows but keep the table structure
# cur.execute("DELETE FROM details;")
cur.execute("DROP TABLE variants;")
conn.commit()

# Optional: reclaim disk space
cur.execute("VACUUM;")

conn.close()
# print("✅ All rows removed from 'details' table.")
print("✅ Drop Variant table.")