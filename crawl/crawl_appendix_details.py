import sqlite3
import time
import requests
import random
import urllib3
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── CONFIGURATION ──────────────────────────────
BASE_URL = "https://dict.variants.moe.edu.tw/"
MAX_WORKERS = 5  # Adjust based on your CPU/Network (5-10 is usually safe)
BATCH_SIZE = 50  # Commit to DB every 50 records

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── SESSION MANAGER ────────────────────────────
def get_session():
    """Creates a session optimized for multithreading"""
    sess = requests.Session()
    # Increase pool size to handle multiple threads
    adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
    sess.mount('http://', adapter)
    sess.mount('https://', adapter)
    
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": BASE_URL,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    })
    return sess

# Global session instance
session = get_session()

# ── HELPER: ROBUST FETCH ───────────────────────
def fetch_page(url):
    """Fetches page content safely"""
    retries = 3
    for attempt in range(retries):
        try:
            # Random sleep per thread to be polite but fast
            time.sleep(random.uniform(0.1, 0.5)) 
            resp = session.get(url, timeout=20, verify=False)
            if resp.status_code == 200:
                return BeautifulSoup(resp.content, "lxml")
        except requests.RequestException:
            pass # Fail silently on individual retry, worker will handle None
    return None

# ── PARSING LOGIC (Preserved from your original script) ──
def parse_tai_icon(soup, result_char, anchor_id):
    appendv = soup.find("div", class_="appendV")
    if not appendv: return None
    target_row = appendv.find("tr", id=anchor_id, class_="act") if anchor_id else None
    if not target_row:
        for row in appendv.find_all("tr", class_="act"):
            char_cell = row.find("td", class_="val")
            if char_cell and char_cell.get_text(strip=True) == result_char:
                target_row = row; break
    if not target_row: return None
    
    data = {}
    char_cell = target_row.find("td", class_="val")
    data['char_form'] = char_cell.get_text(strip=True) if char_cell else ""
    radical_cell = target_row.find("td", class_="idx")
    data['radical_stroke'] = radical_cell.get_text(strip=True) if radical_cell else ""
    sub_cell = target_row.find("td", class_="sub")
    if sub_cell:
        divs = sub_cell.find_all("div")
        if len(divs) >= 2:
            data['pronunciation'] = divs[0].get_text(strip=True)
            data['examples_or_notes'] = divs[1].get_text(strip=True)
        elif len(divs) == 1:
            data['pronunciation'] = divs[0].get_text(strip=True)
            data['examples_or_notes'] = ""
        else:
            data['pronunciation'] = sub_cell.get_text(strip=True)
            data['examples_or_notes'] = ""
    else:
        data['pronunciation'] = ""; data['examples_or_notes'] = ""
    return data

def parse_ke_icon(soup, result_char, anchor_id):
    appendv = soup.find("div", class_="appendV")
    if not appendv: return None
    target_row = appendv.find("tr", id=anchor_id, class_="act") if anchor_id else None
    if not target_row:
        for row in appendv.find_all("tr", class_="act"):
            char_cell = row.find("td", class_="val")
            if char_cell and char_cell.get_text(strip=True) == result_char:
                target_row = row; break
    if not target_row: return None

    data = {}
    char_cell = target_row.find("td", class_="val")
    data['char_form'] = char_cell.get_text(strip=True) if char_cell else ""
    radical_cell = target_row.find("td", class_="idx")
    data['radical_stroke'] = radical_cell.get_text(strip=True) if radical_cell else ""
    sub_cell = target_row.find("td", class_="sub")
    if sub_cell:
        div = sub_cell.find("div")
        data['pronunciation'] = div.get_text(strip=True) if div else sub_cell.get_text(strip=True)
    else:
        data['pronunciation'] = ""
    data['examples_or_notes'] = ""
    return data

def parse_xing_icon(soup, result_char, anchor_id):
    appendv = soup.find("div", class_="appendV")
    if not appendv: return None
    target_row = appendv.find("tr", id=anchor_id, class_="act") if anchor_id else None
    if not target_row:
        for row in appendv.find_all("tr", class_="act"):
            val_cell = row.find("td", class_="val")
            if val_cell:
                link = val_cell.find("a")
                txt = link.get_text(strip=True) if link else val_cell.get_text(strip=True)
                if txt == result_char: target_row = row; break
    if not target_row: return None

    data = {}
    code_cell = target_row.find("td", class_="idx", headers=lambda x: x and "codeH" in x)
    data['char_code'] = code_cell.get_text(strip=True) if code_cell else ""
    val_cell = target_row.find("td", class_="val")
    if val_cell:
        link = val_cell.find("a")
        data['char_form'] = link.get_text(strip=True) if link else val_cell.get_text(strip=True)
    else: data['char_form'] = ""
    radical_cell = target_row.find("td", class_="idx", headers=lambda x: x and "radH" in x)
    data['radical_stroke'] = radical_cell.get_text(strip=True) if radical_cell else ""
    sub_cell = target_row.find("td", class_="sub")
    if sub_cell:
        divs = sub_cell.find_all("div")
        if len(divs) >= 3:
            data['surname_single'] = divs[0].get_text(strip=True)
            data['surname_compound'] = divs[1].get_text(strip=True)
            data['surname_double'] = divs[2].get_text(strip=True)
        else:
            data['surname_single'] = ""; data['surname_compound'] = ""; data['surname_double'] = ""
    else:
        data['surname_single'] = ""; data['surname_compound'] = ""; data['surname_double'] = ""
    data['pronunciation'] = ""; data['examples_or_notes'] = ""
    return data

# ── WORKER FUNCTION ────────────────────────────
def scrape_single_entry(entry):
    """Worker function to process a single DB entry"""
    result_id, search_char, result_char, detail_url, icon_label, anchor_id = entry

    if not detail_url:
        return None

    soup = fetch_page(detail_url)
    if not soup:
        return {'status': 'error', 'msg': f"Failed load: {result_char}", 'id': result_id}

    # Parse based on icon type
    data = None
    if icon_label == "台":
        data = parse_tai_icon(soup, result_char, anchor_id)
    elif icon_label == "客":
        data = parse_ke_icon(soup, result_char, anchor_id)
    elif icon_label == "姓":
        data = parse_xing_icon(soup, result_char, anchor_id)
    
    if data:
        # Attach identifiers for the DB insert
        data['search_result_id'] = result_id
        data['search_char'] = search_char
        data['result_char'] = result_char
        data['icon_label'] = icon_label
        return {'status': 'success', 'data': data}
    else:
        return {'status': 'error', 'msg': f"Failed parse: {result_char} [{icon_label}]", 'id': result_id}

# ── MAIN EXECUTION ─────────────────────────────
def main():
    # 1. Database Setup
    conn = sqlite3.connect("dictionary.db")
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    
    # Create Table (using IF NOT EXISTS is safe)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appendix_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_result_id INTEGER NOT NULL,
        search_char TEXT NOT NULL,
        result_char TEXT NOT NULL,
        icon_label TEXT NOT NULL,
        char_form TEXT,
        radical_stroke TEXT,
        pronunciation TEXT,
        examples_or_notes TEXT,
        char_code TEXT,
        surname_single TEXT,
        surname_compound TEXT,
        surname_double TEXT,
        FOREIGN KEY (search_result_id) REFERENCES search_results(id),
        UNIQUE(search_result_id)
    );
    """)
    conn.commit()

    # 2. Get Pending Entries (Resume Logic)
    # This query strictly filters out IDs that are already in appendix_details
    print("🔍 Scanning database for pending entries...")
    cur.execute("""
        SELECT id, search_char, result_char, detail_url, icon_label, anchor_id
        FROM search_results
        WHERE result_type = 'Appendix'
        AND id NOT IN (SELECT search_result_id FROM appendix_details)
        ORDER BY id
    """)
    entries = cur.fetchall()
    total_entries = len(entries)
    print(f"⏳ Found {total_entries} remaining entries to crawl.")

    if total_entries == 0:
        print("✅ Nothing to do!")
        conn.close()
        return

    # 3. Multithreaded Processing
    print(f"🚀 Starting crawl with {MAX_WORKERS} threads...")
    
    processed_count = 0
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_entry = {executor.submit(scrape_single_entry, entry): entry for entry in entries}
        
        for future in as_completed(future_to_entry):
            result = future.result()
            processed_count += 1
            
            if result and result['status'] == 'success':
                d = result['data']
                try:
                    cur.execute("""
                        INSERT OR IGNORE INTO appendix_details
                        (search_result_id, search_char, result_char, icon_label, 
                         char_form, radical_stroke, pronunciation, examples_or_notes,
                         char_code, surname_single, surname_compound, surname_double)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        d['search_result_id'], d['search_char'], d['result_char'], d['icon_label'],
                        d.get('char_form', ''), d.get('radical_stroke', ''),
                        d.get('pronunciation', ''), d.get('examples_or_notes', ''),
                        d.get('char_code', ''), d.get('surname_single', ''),
                        d.get('surname_compound', ''), d.get('surname_double', '')
                    ))
                    success_count += 1
                    
                    # Print slightly less verbose to save console IO, update on same line
                    print(f"\r[{processed_count}/{total_entries}] ✅ Saved: {d['result_char']}      ", end="")
                    
                except sqlite3.Error as e:
                    print(f"\n❌ DB Error: {e}")

            elif result and result['status'] == 'error':
                print(f"\n⚠️ {result['msg']}")
            
            # Batch commit to speed up DB operations
            if processed_count % BATCH_SIZE == 0:
                conn.commit()
                print(f" [Committed batch]")

    # Final commit
    conn.commit()
    conn.close()
    print(f"\n\n🎉 Completed! Processed {processed_count}, Success: {success_count}")

if __name__ == "__main__":
    main()