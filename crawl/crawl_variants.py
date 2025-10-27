import sqlite3, time, base64, os
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
    img_path TEXT,
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
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "vari")))
    except Exception:
        print(f"⚠️  No variant section for {main_char}")
        continue

    soup = BeautifulSoup(driver.page_source, "html.parser")
    vari_section = soup.find("section", id="vari")
    if not vari_section:
        print("ℹ️ No #vari section")
        continue

    details_block = vari_section.find("details")
    if not details_block:
        print("ℹ️ No <details> in #vari")
        continue

    variant_links = details_block.find_all("a", href=True)
    if not variant_links:
        print("ℹ️ No variant links")
        continue

    saved = 0
    for a in variant_links:
        # Build per-link data
        data_sn = str(a.get("data-sn", "")).strip()  # like "-001"
        suffix = data_sn if data_sn else "-000"
        variant_code = f"{main_code}{suffix}"

        href = urljoin("https://dict.variants.moe.edu.tw/", str(a.get("href", "")))

        # Determine if it’s an image-backed variant
        img = a.find("img")
        variant_char = a.get_text(strip=True) or ""

        img_path = None
        if img:
            src = img.get("src", "")
            # If site provides a data URL, decode and save locally
            if src.startswith("data:image"):
                try:
                    header, b64data = src.split(",", 1)
                    img_bytes = base64.b64decode(b64data)
                    os.makedirs("variant_images", exist_ok=True)
                    file_name = f"{variant_code}.png"
                    img_path = os.path.join("variant_images", file_name)
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"🖼️  Saved image for {variant_code}")
                except Exception as e:
                    print(f"⚠️  Error decoding image for {variant_code}: {e}")
            else:
                # If it's a normal URL (not data:), we could download later if needed
                # Keep path empty but mark variant_char from alt
                pass

            # Use ALT text if present; otherwise mark as image
            alt_text = img.get("alt")
            variant_char = (alt_text or variant_char or "[img]").strip()

        # If visible text is literally a code (sometimes first item), keep it but mark display
        if not variant_char:
            variant_char = "[?]"

        # Insert/replace per variant
        cur.execute("""
            INSERT OR REPLACE INTO variants
            (variant_code, main_code, variant_char, href, img_path)
            VALUES (?, ?, ?, ?, ?)
        """, (variant_code, main_code, variant_char, href, img_path))
        saved += 1

    conn.commit()
    print(f"✅ Saved {saved}/{len(variant_links)} variants for {main_char}")
    time.sleep(0.5)

driver.quit()
conn.close()
print("✅ Finished crawling simplified variant table.")
