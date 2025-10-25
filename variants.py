import sqlite3, time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Configure Selenium ─────────────────────────
options = Options()
options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)

# ── Connect to database ────────────────────────
conn = sqlite3.connect("dictionary.db")
cur  = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

cur.execute("""
CREATE TABLE IF NOT EXISTS variants (
    variant_code TEXT PRIMARY KEY,
    main_code TEXT NOT NULL,
    variant_char TEXT,
    href TEXT,
    FOREIGN KEY(main_code)
        REFERENCES summary(code)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
""")

# ── Get list of main entries ───────────────────
cur.execute("SELECT code, char, detail_url FROM summary")
entries = cur.fetchall()
print(f"Total entries: {len(entries)}")

# ── Crawl each detail page ─────────────────────
for i, (main_code, main_char, url) in enumerate(entries, 1):
    print(f"[{i}/{len(entries)}] Fetching {main_char} → {url}")
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "vari"))
        )
    except Exception:
        print(f"⚠️  No variant section for {main_char}")
        continue

    soup = BeautifulSoup(driver.page_source, "html.parser")
    vari_section = soup.find("section", id="vari")
    if not vari_section:
        continue

    details_block = vari_section.find("details")
    if not details_block:
        continue

    variant_links = details_block.find_all("a", href=True)
    if not variant_links:
        continue

    for a in variant_links:
        # Build the variant code: main_code + data_sn (e.g. A00001-001)
        data_sn = str(a.get("data-sn", "")).strip()  # "-001"
        suffix = data_sn if data_sn else "-000"
        variant_code = f"{main_code}{suffix}"

        variant_char = a.get_text(strip=True)
        if not variant_char:
            img = a.find("img")
            if img and img.get("alt"):
                variant_char = img["alt"]

        href = urljoin("https://dict.variants.moe.edu.tw/", str(a.get("href", "")))

        cur.execute("""
            INSERT OR REPLACE INTO variants
            (variant_code, main_code, variant_char, href)
            VALUES (?, ?, ?, ?)
        """, (variant_code, main_code, variant_char, href))

    conn.commit()
    print(f"✅ Saved {len(variant_links)} variants for {main_char}")
    time.sleep(1.2)

driver.quit()
conn.close()
print("✅ Finished crawling simplified variant table.")