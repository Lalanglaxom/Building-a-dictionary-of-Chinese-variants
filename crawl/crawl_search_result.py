import sqlite3
import time
import requests
import re
import random
import urllib3
import os
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup

# ── CONFIGURATION ──────────────────────────────
BASE_URL = "https://dict.variants.moe.edu.tw/"
SEARCH_URL = "https://dict.variants.moe.edu.tw/search.jsp"

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── DATABASE SETUP ─────────────────────────────
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")
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
conn.commit()

cur.execute("""
    SELECT code, char 
    FROM summary 
    WHERE char NOT IN (SELECT DISTINCT search_char FROM search_results)
    ORDER BY code
""")
entries = cur.fetchall()
print(f"⏳ Remaining to search: {len(entries)}")

# ── SESSION MANAGER ────────────────────────────
def get_new_session():
    """Creates a fresh session with browser-like headers"""
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": BASE_URL,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    })
    return sess

session = get_new_session()

# ── HELPER: ROBUST FETCH ───────────────────────
def fetch_page(url, params=None, retry_session=False):
    """Fetches page. If retry_session is True, creates new session on failure."""
    global session
    retries = 3
    
    for attempt in range(retries):
        try:
            resp = session.get(url, params=params, timeout=15, verify=False)
            if resp.status_code == 200:
                # Use lxml for speed and robustness
                return BeautifulSoup(resp.content, "lxml")
            
        except requests.RequestException as e:
            print(f"  ⚠️ Network error (Attempt {attempt+1}): {e}")
            time.sleep(2)
            
            # If we are failing repeatedly, refresh session
            if attempt == retries - 1 and retry_session:
                print("  🔄 Refreshing Session...")
                session = get_new_session()
                
    return None

# ── MAIN LOOP ──────────────────────────────────
for i, (main_code, main_char) in enumerate(entries, 1):
    print(f"\n[{i}/{len(entries)}] Searching: {main_char} ({main_code})")
    
    # 1. SEARCH
    # We add a random delay to avoid rate limiting
    time.sleep(random.uniform(0.5, 1.2))
    
    params = {'QTP': '0', 'WORD': main_char}
    soup = fetch_page(SEARCH_URL, params)
    
    if not soup:
        print("❌ Failed to load search page")
        continue

    search_section = soup.find("div", id="searchL")
    if not search_section:
        print("ℹ️  No searchL section found")
        continue

    # 2. PARSE COUNTS
    text_count = 0
    appendix_count = 0
    
    # Text Count
    text_link = search_section.find("a", string=re.compile(r"正文"))
    if text_link:
        match = re.search(r'\((\d+)\)', text_link.get_text(strip=True))
        if match: text_count = int(match.group(1))

    # Appendix Count
    appendix_link = search_section.find("a", string=re.compile(r"附收字"))
    if appendix_link:
        match = re.search(r'\((\d+)\)', appendix_link.get_text(strip=True))
        if match: appendix_count = int(match.group(1))

    print(f"📝 Text entries: {text_count}, Appendix entries: {appendix_count}")

    # ── LOGIC FOR "GHOST" CONTENT (Count > 0 but no items) ──
    # This block handles the specific error you are seeing
    
    # ════════ PART 1: TEXT ════════
    if text_count > 0:
        text_boxes = search_section.find_all("a", href=lambda x: x and "dictView.jsp" in x)
        
        # SELF-HEALING: If count says yes, but boxes say no
        if len(text_boxes) == 0:
            print("  ⚠️ Mismatch detected! Refreshing session and waiting...")
            
            # 1. Kill session and sleep
            session = get_new_session()
            time.sleep(5.0) # Longer sleep to clear rate limit
            
            # 2. Force fetch Text Tab specifically (TP=1)
            params['TP'] = '1'
            soup = fetch_page(SEARCH_URL, params)
            if soup:
                search_section = soup.find("div", id="searchL")
                text_boxes = search_section.find_all("a", href=lambda x: x and "dictView.jsp" in x)
            
            # 3. If STILL zero, dump debug file
            if len(text_boxes) == 0:
                print("  ❌ STILL ZERO after retry. Dumping HTML to 'debug_error.html'")
                with open("debug_error.html", "w", encoding="utf-8") as f:
                    f.write(str(soup))
        
        print(f"📚 Processing {len(text_boxes)} text entry/entries")
        
        for box in text_boxes:
            # (Extraction logic same as before)
            result_char = box.get_text(strip=True)
            href = box.get("href", "")
            detail_url = urljoin(BASE_URL, href)
            
            code_tag = box.find("code")
            result_code, ucs_code, radical_stroke = "", "", ""
            if code_tag:
                lines = code_tag.get_text(strip=True).split('\n')
                if len(lines) > 0: result_code = lines[0].strip()
                if len(lines) > 1: ucs_code = lines[1].strip()
                if len(lines) > 2: radical_stroke = lines[2].strip()
                code_tag.extract()
            
            data_sn = box.get("data-sn")
            if not ucs_code: ucs_code = box.get("data-ucs", "")
            
            print(f"  📄 Text: {result_char} [{result_code}]")
            cur.execute("""
                INSERT OR IGNORE INTO search_results
                (search_char, result_type, result_char, result_code, detail_url, data_sn, ucs_code, radical_stroke)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (main_char, "Text", result_char, result_code, detail_url, data_sn, ucs_code, radical_stroke))

    # ════════ PART 2: APPENDIX ════════
    if appendix_count > 0:
        # Always use clean params for Appendix
        app_params = {'QTP': '0', 'WORD': main_char, 'TP': '2'}
        time.sleep(0.3)
        
        app_soup = fetch_page(SEARCH_URL, app_params)
        
        if app_soup:
            app_section = app_soup.find("div", id="searchL")
            appendix_boxes = []
            if app_section:
                appendix_boxes = app_section.find_all("a", href=lambda x: x and "appendix.jsp" in x)
            
            # SELF-HEALING FOR APPENDIX
            if len(appendix_boxes) == 0:
                print("  ⚠️ Appendix mismatch! Retrying...")
                time.sleep(3.0)
                app_soup = fetch_page(SEARCH_URL, app_params)
                if app_soup and app_soup.find("div", id="searchL"):
                    appendix_boxes = app_soup.find("div", id="searchL").find_all("a", href=lambda x: x and "appendix.jsp" in x)

            print(f"📑 Found {len(appendix_boxes)} appendix link(s)")
            
            for box in appendix_boxes:
                # (Extraction logic same as before)
                result_char = box.get_text(strip=True)
                icon_label = box.get("data-tp", "").strip()
                href = box.get("href", "")
                detail_url = urljoin(BASE_URL, href)
                
                appendix_id, anchor_id = "", ""
                if detail_url:
                    parsed = urlparse(detail_url)
                    qs = parse_qs(parsed.query)
                    appendix_id = qs.get('ID', [''])[0]
                    anchor_id = parsed.fragment
                
                ucs_code = box.get("data-ucs", "")
                radical_stroke = box.get("data-rad", "")
                
                print(f"  📋 Appendix: {result_char} [{icon_label}]")
                cur.execute("""
                    INSERT OR IGNORE INTO search_results
                    (search_char, result_type, result_char, detail_url, appendix_id, anchor_id, icon_label, ucs_code, radical_stroke)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (main_char, "Appendix", result_char, detail_url, appendix_id, anchor_id, icon_label, ucs_code, radical_stroke))

    conn.commit()

conn.close()
print("✅ Done!")