import sqlite3
import time
import os
from urllib.parse import urljoin, urlencode
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Configure Selenium ─────────────────────────
options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

# ── Connect to database ────────────────────────
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

# Create supplementary_chars table
cur.execute("""
CREATE TABLE IF NOT EXISTS supplementary_chars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    main_char TEXT NOT NULL,
    main_code TEXT NOT NULL,
    supplementary_code TEXT,
    supplementary_char TEXT,
    appendix_count INTEGER DEFAULT 0,
    search_url TEXT,
    appendix_url TEXT,
    detail_url TEXT,
    icon_label TEXT,
    FOREIGN KEY(main_code)
        REFERENCES summary(code)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
""")

# Create index for faster lookups
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_supp_main_code 
ON supplementary_chars(main_code);
""")

conn.commit()

# ── Get list of main entries ───────────────────
cur.execute("SELECT code, char FROM summary ORDER BY code")
entries = cur.fetchall()
print(f"📊 Total entries to search: {len(entries)}")

BASE_URL = "https://dict.variants.moe.edu.tw/"
SEARCH_URL = "https://dict.variants.moe.edu.tw/search.jsp"

# ── Search each character ──────────────────────
for i, (main_code, main_char) in enumerate(entries, 1):
    print(f"\n[{i}/{len(entries)}] Searching: {main_char} ({main_code})")
    
    # Build search URL with Quick Search (QTP=0)
    params = {
        'QTP': '0',
        'WORD': main_char
    }
    search_url = f"{SEARCH_URL}?{urlencode(params)}#searchL"
    
    try:
        driver.get(search_url)
        # Wait for search results
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "searchL"))
        )
        time.sleep(1)  # Additional wait for dynamic content
        
    except Exception as e:
        print(f"⚠️  Error loading search page: {e}")
        continue
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Find the search results section
    search_section = soup.find("div", id="searchL")
    if not search_section:
        print("ℹ️  No searchL section found")
        continue
    
    # Look for the tab links to check Text and Appendix counts
    tab_div = search_section.find("div")
    text_count = 0
    appendix_count = 0
    appendix_url = None
    
    if tab_div:
        # Parse "Text (1)" link
        text_link = tab_div.find("a", href=lambda x: x and "TP=2" not in x)
        if text_link:
            text_text = text_link.get_text(strip=True)
            # Extract number from "Text (1)"
            import re
            match = re.search(r'\((\d+)\)', text_text)
            if match:
                text_count = int(match.group(1))
        
        # Parse "Appendix (3)" link
        appendix_link = tab_div.find("a", href=lambda x: x and "TP=2" in x)
        if appendix_link:
            appendix_text = appendix_link.get_text(strip=True)
            # Extract number from "Appendix (3)"
            match = re.search(r'\((\d+)\)', appendix_text)
            if match:
                appendix_count = int(match.group(1))
                appendix_url = urljoin(BASE_URL, appendix_link.get("href", ""))
    
    print(f"📝 Text entries: {text_count}, Appendix entries: {appendix_count}")
    
    # If there are appendix entries, we need to crawl them
    if appendix_count > 0 and appendix_url:
        print(f"🔗 Appendix URL: {appendix_url}")
        
        try:
            driver.get(appendix_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "selectL"))
            )
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠️  Error loading appendix page: {e}")
            continue
        
        appendix_soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Find all supplementary character boxes
        # They appear as <a> tags with data-tp attribute for the icon label
        supp_boxes = appendix_soup.find_all("a", {"data-tp": True, "href": lambda x: x and "appendix.jsp" in x})
        
        print(f"🔍 Found {len(supp_boxes)} supplementary character(s)")
        
        for box in supp_boxes:
            # Extract character
            supp_char = box.get_text(strip=True).split('\n')[0] if box.get_text() else ""
            
            # Extract icon label (台/客/姓 etc.)
            icon_label = box.get("data-tp", "").strip()
            
            # Extract detail URL
            detail_href = box.get("href", "")
            detail_url = urljoin(BASE_URL, detail_href) if detail_href else ""
            
            # Extract code from the <code> tag inside
            code_tag = box.find("code")
            supplementary_code = ""
            if code_tag:
                code_lines = code_tag.get_text(strip=True).split('\n')
                if code_lines:
                    # First line is usually the code (e.g., "A00005")
                    supplementary_code = code_lines[0].strip()
            
            # If character text contains the code, clean it
            if supp_char and supplementary_code and supplementary_code in supp_char:
                supp_char = supp_char.replace(supplementary_code, "").strip()
            
            print(f"  📌 {supp_char} [{supplementary_code}] - {icon_label} → {detail_url}")
            
            # Insert into database
            cur.execute("""
                INSERT INTO supplementary_chars
                (main_char, main_code, supplementary_code, supplementary_char, 
                 appendix_count, search_url, appendix_url, detail_url, icon_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                main_char, 
                main_code, 
                supplementary_code, 
                supp_char,
                appendix_count,
                search_url,
                appendix_url,
                detail_url,
                icon_label
            ))
        
        conn.commit()
        print(f"✅ Saved {len(supp_boxes)} supplementary characters for {main_char}")
    
    else:
        print(f"ℹ️  No appendix entries for {main_char}")
    
    # Respectful delay
    time.sleep(0.8)

# ── Cleanup ────────────────────────────────────
driver.quit()
conn.close()

print("\n" + "="*50)
print("✅ Finished crawling supplementary characters!")
print("="*50)

# Show summary statistics
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM supplementary_chars")
total_supp = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT main_code) FROM supplementary_chars")
chars_with_supp = cur.fetchone()[0]

print(f"📊 Total supplementary characters collected: {total_supp}")
print(f"📊 Main characters with supplementary entries: {chars_with_supp}")

# Show icon label distribution
cur.execute("""
    SELECT icon_label, COUNT(*) 
    FROM supplementary_chars 
    GROUP BY icon_label 
    ORDER BY COUNT(*) DESC
""")
print("\n📋 Distribution by icon label:")
for label, count in cur.fetchall():
    print(f"  {label}: {count}")

conn.close()