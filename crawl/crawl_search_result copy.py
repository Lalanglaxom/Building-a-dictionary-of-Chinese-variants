import sqlite3
import time
import os
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ── HELPER: Start a new driver ─────────────────
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage") # Fixes resource issues in containers/Linux
    options.page_load_strategy = 'eager'  # Don't wait for all images to load
    return webdriver.Chrome(options=options)

driver = get_driver()

# ── Connect to database ────────────────────────
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

# Create search_results table to store ALL search results (Text + Appendix)
cur.execute("""
CREATE TABLE IF NOT EXISTS search_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_char TEXT NOT NULL,
    result_type TEXT NOT NULL,
    result_char TEXT,
    result_code TEXT,
    detail_url TEXT,
    appendix_id TEXT,
    anchor_id TEXT,
    icon_label TEXT,
    data_sn INTEGER,
    ucs_code TEXT,
    radical_stroke TEXT,
    UNIQUE(search_char, result_type, result_code, appendix_id, anchor_id)
);
""")

# Create index
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_search_char 
ON search_results(search_char);
""")

conn.commit()

# ── Get list of main entries ───────────────────
# Only get characters that haven't been searched yet
cur.execute("""
    SELECT code, char 
    FROM summary 
    WHERE char NOT IN (SELECT DISTINCT search_char FROM search_results)
    ORDER BY code
""")
entries = cur.fetchall()

# Also show total progress
cur.execute("SELECT COUNT(*) FROM summary")
total_chars = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT search_char) FROM search_results")
already_searched = cur.fetchone()[0]

print(f"📊 Total characters in summary: {total_chars}")
print(f"✅ Already searched: {already_searched}")
print(f"⏳ Remaining to search: {len(entries)}")

BASE_URL = "https://dict.variants.moe.edu.tw/"
SEARCH_URL = "https://dict.variants.moe.edu.tw/search.jsp"

# ── ROBUST SEARCH LOOP ─────────────────────────
for i, (main_code, main_char) in enumerate(entries, 1):
    print(f"\n[{i}/{len(entries)}] Searching: {main_char} ({main_code})")
    
    params = { 'QTP': '0', 'WORD': main_char }
    search_url = f"{SEARCH_URL}?{urlencode(params)}#searchL"
    
    # RETRY LOGIC: Try loading the page up to 3 times
    max_retries = 3
    success = False
    
    for attempt in range(max_retries):
        try:
            driver.get(search_url)
            # Wait for container
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "searchL")))
            success = True
            break # Success! Exit retry loop
            
        except (TimeoutException, WebDriverException) as e:
            print(f"⚠️  Attempt {attempt+1}/{max_retries} failed: {e}")
            
            # If it failed, restart the driver completely
            print("🔄 Restarting driver...")
            try:
                driver.quit()
            except:
                pass
            time.sleep(2)
            driver = get_driver()
            
    if not success:
        print(f"❌ Skipping {main_char} after {max_retries} failed attempts.")
        continue

    # ── IF WE GET HERE, THE PAGE LOADED SUCCESSFULLY ──
    
    # 1. Parse Counts
    soup = BeautifulSoup(driver.page_source, "html.parser")
    search_section = soup.find("div", id="searchL")
    if not search_section:
        continue

    text_count = 0
    appendix_count = 0
    import re
    
    # Find Text Link
    text_tab_link = search_section.find("a", string=re.compile(r"正文"))
    text_force_url = ""
    if text_tab_link:
        match = re.search(r'\((\d+)\)', text_tab_link.get_text(strip=True))
        if match: text_count = int(match.group(1))
        href = text_tab_link.get("href")
        if href: text_force_url = urljoin(BASE_URL, href)

    # Find Appendix Link
    appendix_tab_link = search_section.find("a", string=re.compile(r"附收字"))
    appendix_force_url = ""
    if appendix_tab_link:
        match = re.search(r'\((\d+)\)', appendix_tab_link.get_text(strip=True))
        if match: appendix_count = int(match.group(1))
        href = appendix_tab_link.get("href")
        if href: appendix_force_url = urljoin(BASE_URL, href)

    print(f"📝 Text entries: {text_count}, Appendix entries: {appendix_count}")

    # ════════ PART 1: TEXT ════════
    if text_count > 0:
        try:
            # Force switch to Text tab if not active
            if text_tab_link and "act" not in text_tab_link.get("class", []):
                driver.get(text_force_url if text_force_url else (search_url + "&TP=1"))
            
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#searchL a[href*='dictView.jsp']"))
            )
            
            # Re-parse
            soup = BeautifulSoup(driver.page_source, "html.parser")
            search_section = soup.find("div", id="searchL")
            text_boxes = search_section.find_all("a", href=lambda x: x and "dictView.jsp" in x)
            
            print(f"📚 Processing {len(text_boxes)} text entry/entries")
            
            for box in text_boxes:
                # -- Parsing Logic (Identical to before) --
                box_text = box.get_text(strip=True)
                code_tag = box.find("code")
                if code_tag:
                    code_content = code_tag.get_text(strip=True)
                    lines = code_content.split('\n')
                    result_code = lines[0].strip() if len(lines) > 0 else ""
                    ucs_code = lines[1].strip() if len(lines) > 1 else ""
                    radical_stroke = lines[2].strip() if len(lines) > 2 else ""
                    code_tag.extract()
                else:
                    result_code = ""
                    ucs_code = ""
                    radical_stroke = ""

                result_char = box.get_text(strip=True)
                detail_url = urljoin(BASE_URL, box.get("href", ""))
                data_sn = box.get("data-sn", "")
                try: data_sn = int(data_sn) if data_sn else None
                except: data_sn = None
                if not ucs_code: ucs_code = box.get("data-ucs", "")

                cur.execute("""
                    INSERT OR IGNORE INTO search_results
                    (search_char, result_type, result_char, result_code, 
                     detail_url, data_sn, ucs_code, radical_stroke)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (main_char, "Text", result_char, result_code, detail_url, data_sn, ucs_code, radical_stroke))
                conn.commit()

        except Exception as e:
            print(f"⚠️  Error getting Text results: {e}")

    # ════════ PART 2: APPENDIX ════════
    if appendix_count > 0:
        try:
            target_url = appendix_force_url if appendix_force_url else (search_url + "&TP=2")
            driver.get(target_url)

            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#searchL a[href*='appendix.jsp']"))
            )
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            search_section = soup.find("div", id="searchL")
            appendix_boxes = search_section.find_all("a", href=lambda x: x and "appendix.jsp" in x)
            
            print(f"📑 Found {len(appendix_boxes)} appendix link(s)")

            for box in appendix_boxes:
                # -- Parsing Logic --
                result_char = box.get_text(strip=True)
                icon_label = box.get("data-tp", "").strip()
                detail_url = urljoin(BASE_URL, box.get("href", ""))
                
                appendix_id = ""
                anchor_id = ""
                if detail_url:
                    parsed = urlparse(detail_url)
                    q = parse_qs(parsed.query)
                    appendix_id = q.get('ID', [''])[0]
                    anchor_id = parsed.fragment
                
                ucs_code = box.get("data-ucs", "")
                radical_stroke = box.get("data-rad", "")

                cur.execute("""
                    INSERT OR IGNORE INTO search_results
                    (search_char, result_type, result_char, result_code,
                     detail_url, appendix_id, anchor_id, icon_label,
                     ucs_code, radical_stroke)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (main_char, "Appendix", result_char, None, detail_url, appendix_id, anchor_id, icon_label, ucs_code, radical_stroke))
                conn.commit()

        except Exception as e:
            print(f"⚠️  Error getting Appendix results: {e}")

# Cleanup at the very end
driver.quit()
conn.close()

print("\n" + "="*50)
print("✅ Finished crawling search results!")
print("="*50)

# Show summary statistics
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM search_results WHERE result_type='Text'")
total_text = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM search_results WHERE result_type='Appendix'")
total_appendix = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT search_char) FROM search_results")
chars_with_results = cur.fetchone()[0]

print(f"📊 Total Text entries: {total_text}")
print(f"📊 Total Appendix entries: {total_appendix}")
print(f"📊 Characters with search results: {chars_with_results}")

# Show icon label distribution for appendix
cur.execute("""
    SELECT icon_label, COUNT(*) 
    FROM search_results 
    WHERE result_type='Appendix'
    GROUP BY icon_label 
    ORDER BY COUNT(*) DESC
""")
print("\n📋 Appendix distribution by type:")
for label, count in cur.fetchall():
    label_name = {
        '台': 'Taiwanese (台)',
        '客': 'Hakka (客)',
        '姓': 'Surname (姓)',
        '雜': 'Miscellaneous (雜)'
    }.get(label, label)
    print(f"  {label_name}: {count}")

# Show examples of characters with multiple text entries
cur.execute("""
    SELECT search_char, COUNT(*) as cnt
    FROM search_results
    WHERE result_type='Text'
    GROUP BY search_char
    HAVING cnt > 1
    LIMIT 5
""")
multi_text = cur.fetchall()
if multi_text:
    print("\n📋 Examples of characters with multiple Text entries:")
    for char, cnt in multi_text:
        print(f"  {char}: {cnt} entries")

conn.close()