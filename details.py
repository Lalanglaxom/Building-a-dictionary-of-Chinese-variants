import time
import sqlite3
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Connect to the database ──────────────────────────────
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()

# ── Create table for variant links only ──────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS variant_links (
    main_code TEXT,
    main_char TEXT,
    variant_char TEXT,
    href TEXT,
    data_ucs TEXT,
    data_sn TEXT,
    data_tp TEXT
)
""")

# ── Pull list of character detail pages to crawl ─────────
cur.execute("SELECT code, char, detail_url FROM summary")
entries = cur.fetchall()

# ── Crawl each page ─────────────────────────────────────
for i, (main_code, main_char, url) in enumerate(entries, 1):
    print(f"[{i}/{len(entries)}] Fetching {main_char} → {url}")

    try:
        r = requests.get(url, timeout=10, verify=False)
        r.raise_for_status()
    except requests.RequestException as e:
        print("❌ Request error:", e)
        continue

    soup = BeautifulSoup(r.text, "html.parser")

    # --- find variants inside <section id="vari"> ---
    vari_section = soup.find("section", id="vari")
    if not vari_section:
        print('no vari section')
        continue

    detail_block = vari_section.find("details")
    if not detail_block:
        continue

    variant_links = detail_block.find_all("a", href=True)
    for a in variant_links:
        relative = str(a.get("href", ""))
        href = urljoin("https://dict.variants.moe.edu.tw/", relative)
        data_ucs = str(a.get("data-ucs") or "")
        data_sn = str(a.get("data-sn") or "")
        data_tp = str(a.get("data-tp") or "")

        # Variant can be either text or alt of an <img>
        variant_char = a.get_text(strip=True)
        if not variant_char:
            img = a.find("img")
            if img and img.get("alt"):
                variant_char = img["alt"]

        cur.execute("""
            INSERT INTO variant_links (main_code, main_char, variant_char, href, data_ucs, data_sn, data_tp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (main_code, main_char, variant_char, href, data_ucs, data_sn, data_tp))

    conn.commit()
    time.sleep(1)  # polite delay

conn.close()
print("✅ Finished crawling all variant sections.")