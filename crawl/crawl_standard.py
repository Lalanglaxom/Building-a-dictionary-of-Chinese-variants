import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Base URL pattern for the site
BASE_URL = r"https://dict.variants.moe.edu.tw/appendix.jsp?ID=1&page={}"

# Connect to SQLite (creates the file if it doesn't exist)
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()

# Table to store summary data
cur.execute("""
CREATE TABLE IF NOT EXISTS summary (
    code TEXT PRIMARY KEY,
    char TEXT,
    radical TEXT,
    detail_url TEXT
)
""")

# Loop through all 300 pages
for page_num in range(1, 301):
    url = BASE_URL.format(page_num)
    print(f"Fetching page {page_num} → {url}")

    try:
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching page {page_num}: {e}")
        continue

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all <tr id=...> elements (each entry)
    rows = soup.find_all("tr", id=True)

    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 3:
            continue

        code = tds[0].get_text(strip=True)
        char_link = tds[1].find("a")
        if not char_link:
            continue
        char = char_link.get_text(strip=True)
        detail_link = char_link["href"]
        # Make the link absolute (so it can be fetched later)
        detail_url = f"https://dict.variants.moe.edu.tw/{detail_link}"
        radical = tds[2].get_text(strip=True)

        cur.execute("""
            INSERT OR REPLACE INTO summary (code, char, radical, detail_url)
            VALUES (?, ?, ?, ?)
        """, (code, char, radical, detail_url))

    conn.commit()
    print(f"✔ Saved entries from page {page_num}")
    time.sleep(1)  # be polite to the server

conn.close()
print("✅ All pages processed and saved to dictionary.db")