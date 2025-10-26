import sqlite3, time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
import os

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

# Check existing columns in the table
cur.execute("PRAGMA table_info(variants);")
columns = [col[1] for col in cur.fetchall()]  # list of column names

# Add img_path only if it doesn’t exist
if "img_path" not in columns:
    cur.execute("ALTER TABLE variants ADD COLUMN img_path TEXT;")
    conn.commit()
    print("✅ Added column 'img_path' to variants.")
else:
    print("ℹ️ Column 'img_path' already exists.")

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
        data_sn = str(a.get("data-sn", "")).strip()  # "-001"
        suffix  = data_sn if data_sn else "-000"
        variant_code = f"{main_code}{suffix}"

        img = a.find("img")
        variant_char = a.get_text(strip=True)
        img_path = None  # optional path field

    # treat as image variant if there's an <img> OR the visible text looks like a code
    if img or variant_char.startswith(main_code):
        if img:
            src = img.get("src", "")
            if src and src.startswith("data:image"): # Okay
                try:
                    header, b64data = src.split(",", 1)
                    img_bytes = base64.b64decode(b64data)

                    os.makedirs("variant_images", exist_ok=True)
                    file_name = f"{variant_code}.png"
                    img_path  = os.path.join("variant_images", file_name)

                    with open(img_path, "wb") as f:
                        f.write(img_bytes)

                    print(f"🖼️  Saved image for {variant_code}")
                except Exception as e:
                    print(f"⚠️  Error decoding image for {variant_code}: {e}")
            else:
                print(f"ℹ️  No image data for {variant_code}")

            # set display text
            variant_char = img.get("alt", "[img]") or "[img]"
        else:
            # had no <img>, only a code‑like text — keep the text as marker
            variant_char = variant_char or "[img]"

    # text‑only variant: keep normal glyph
    else:
        variant_char = variant_char or "[?]"

        href = urljoin("https://dict.variants.moe.edu.tw/", str(a.get("href", "")))

        cur.execute("""
            INSERT OR REPLACE INTO variants
            (variant_code, main_code, variant_char, href, img_path)
            VALUES (?, ?, ?, ?, ?)
        """, (variant_code, main_code, variant_char, href, img_path))

    conn.commit()
    print(f"✅ Saved {len(variant_links)} variants for {main_char}")
    time.sleep(1)

driver.quit()
conn.close()
print("✅ Finished crawling simplified variant table.")