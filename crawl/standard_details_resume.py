from bs4 import BeautifulSoup
import sqlite3, os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import base64

options = Options()
options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)

conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")
cur.execute("""
CREATE TABLE IF NOT EXISTS descriptions (
    main_code TEXT PRIMARY KEY,
    main_char TEXT,
    standard_character TEXT,
    shuowen_etymology TEXT,
    character_style TEXT,
    zhuyin_pronunciation TEXT,
    hanyu_pinyin TEXT,
    definition TEXT,
    FOREIGN KEY(main_code)
        REFERENCES summary(code)
        ON DELETE CASCADE
);
""")

# Get total count of entries
cur.execute("SELECT COUNT(*) FROM summary;")
total_entries = cur.fetchone()[0]
print(f"Total entries in database: {total_entries}\n")

# Check for last processed entry
cur.execute("SELECT main_code, main_char FROM descriptions ORDER BY ROWID DESC LIMIT 1;")
last_processed = cur.fetchone()

START_INDEX = None
RESUME_MESSAGE = ""

if last_processed:
    last_code, last_char = last_processed
    print(f"✅ Found last processed entry:")
    print(f"   Code: {last_code}")
    print(f"   Character: {last_char}\n")
    
    # Get the position of this entry
    cur.execute("SELECT ROWID FROM summary WHERE code = ?;", (last_code,))
    last_rowid = cur.fetchone()
    
    if last_rowid:
        last_position = last_rowid[0]
        START_INDEX = last_position + 1
        RESUME_MESSAGE = f"Resuming from index {START_INDEX} (skipping first {last_position} entries)"
        print(f"📍 {RESUME_MESSAGE}\n")
else:
    print("❌ No previous entries found in database")
    START_INDEX = 1
    RESUME_MESSAGE = "Starting from beginning (index 1)"
    print(f"📍 {RESUME_MESSAGE}\n")

# Calculate offset for SQL query
OFFSET = START_INDEX - 1

print(f"Fetching entries from index {START_INDEX} to {total_entries}...")
print(f"Total entries to process: {total_entries - OFFSET}\n")

# Pull entries from START_INDEX onwards
cur.execute("SELECT ROWID, code, char, detail_url FROM summary LIMIT -1 OFFSET ?;", (OFFSET,))
entries = cur.fetchall()

def extract_td_text(td, code_prefix, folder="summary_images"):
    """
    Converts a <td> to plain text, saving inline base64 images to PNG files.
    Returns text with image path placeholders like [img:path/to/image.png]
    """
    os.makedirs(folder, exist_ok=True)
    text_parts = []
    img_counter = 0
    
    for elem in td.descendants:
        if elem.name == "img" and elem.get("src", "").startswith("data:image"):
            alt = elem.get("alt", "[image]")
            src = elem["src"]
            try:
                # Extract base64 data
                _, b64data = src.split(",", 1)
                img_bytes = base64.b64decode(b64data)
                
                # Save image file
                file_name = f"{code_prefix}_img_{img_counter}.png"
                img_path = os.path.join(folder, file_name)
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                
                text_parts.append(f"[img:{img_path}]")
                img_counter += 1
            except Exception as e:
                print(f"  ⚠️  Image extraction error: {e}")
                text_parts.append("[img_error]")
        
        elif elem.name is None and str(elem).strip():
            text_parts.append(str(elem).strip())
    
    return "".join(text_parts).strip()

def parse_table_row(row):
    """
    Parses a single table row and returns (label, content)
    """
    th = row.find("th")
    td = row.find("td")
    
    if not th or not td:
        return None, None
    
    label = th.get_text(strip=True)
    return label, td

def map_label_to_field(label):
    """
    Maps Chinese table row labels to English database field names
    """
    # Chinese to English field mapping
    label_mapping = {
        "正　　字": "standard_character",
        "正字": "standard_character",
        "說文釋形": "shuowen_etymology",
        "說文": "shuowen_etymology",
        "字樣說明": "character_style",
        "字樣": "character_style",
        "注　　音": "zhuyin_pronunciation",
        "注音": "zhuyin_pronunciation",
        "漢語拼音": "hanyu_pinyin",
        "拼音": "hanyu_pinyin",
        "釋　　義": "definition",
        "釋義": "definition",
    }
    
    # Try exact match first
    if label in label_mapping:
        return label_mapping[label]
    
    # Try keyword matching
    if "正字" in label or "正　　字" in label:
        return "standard_character"
    elif "說文" in label:
        return "shuowen_etymology"
    elif "字樣" in label:
        return "character_style"
    elif "注" in label and "音" in label:
        return "zhuyin_pronunciation"
    elif "拼音" in label:
        return "hanyu_pinyin"
    elif "釋" in label or "義" in label:
        return "definition"
    
    return None

# Track progress
successful = 0
failed = 0
start_time = time.time()

print(f"{'='*70}")
print(f"Starting scraping session...")
print(f"{'='*70}\n")

for idx, (rowid, main_code, main_char, url) in enumerate(entries, 1):
    current_index = START_INDEX + idx - 1
    progress_percent = (idx / len(entries)) * 100
    
    print(f"\n[{current_index}/{total_entries}] ({progress_percent:.1f}%) Processing: {main_char} (Code: {main_code})")
    print(f"    URL: {url}")
    
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "view"))
        )
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Find the table
        table = soup.find("table", id="view")
        if not table:
            print(f"    ⚠️  No table found for {main_char}")
            failed += 1
            continue
        
        # Initialize data dictionary with English field names
        data = {
            "main_code": main_code,
            "main_char": main_char,
            "standard_character": None,
            "shuowen_etymology": None,
            "character_style": None,
            "zhuyin_pronunciation": None,
            "hanyu_pinyin": None,
            "definition": None,
        }
        
        # Parse all rows
        for row in table.find_all("tr"):
            label, td = parse_table_row(row)
            
            if not label or not td:
                continue
            
            # Map label to field
            field = map_label_to_field(label)
            
            if field:
                # Extract text and images
                content = extract_td_text(td, main_code)
                data[field] = content
                print(f"    ✓ {label}")
            else:
                print(f"    ? Unknown field: {label}")
        
        # Insert into database with English field names
        cur.execute("""
            INSERT OR REPLACE INTO descriptions
            (main_code, main_char, standard_character, shuowen_etymology, 
             character_style, zhuyin_pronunciation, hanyu_pinyin, definition)
            VALUES (:main_code, :main_char, :standard_character, :shuowen_etymology,
                    :character_style, :zhuyin_pronunciation, :hanyu_pinyin, :definition)
        """, data)
        conn.commit()
        
        print(f"    ✅ Successfully saved to database")
        successful += 1
        time.sleep(1.0)
        
    except Exception as e:
        print(f"    ❌ Error processing {main_char}: {e}")
        failed += 1
        time.sleep(2.0)  # Wait longer on error
        continue

driver.quit()
conn.close()

# Calculate statistics
elapsed_time = time.time() - start_time
elapsed_minutes = elapsed_time / 60
elapsed_hours = elapsed_minutes / 60

print(f"\n{'='*70}")
print(f"✅ Scraping session completed!")
print(f"{'='*70}")
print(f"📊 Statistics:")
print(f"   Total entries processed: {len(entries)}")
print(f"   Successful: {successful}")
print(f"   Failed: {failed}")
print(f"   Success rate: {(successful/len(entries)*100):.1f}%")
print(f"   Starting index: {START_INDEX}")
print(f"   Ending index: {total_entries}")
print(f"   Time elapsed: {elapsed_hours:.2f}h ({elapsed_minutes:.1f}m)")
if len(entries) > 0:
    avg_time = elapsed_time / len(entries)
    print(f"   Avg time per entry: {avg_time:.2f}s")
print(f"{'='*70}")

# Show next steps
cur.execute("SELECT COUNT(*) FROM descriptions;")
total_processed = cur.fetchone()[0]
print(f"\n📝 Summary:")
print(f"   Total entries in descriptions table: {total_processed}")
print(f"   Remaining entries to process: {total_entries - total_processed}")
if total_processed < total_entries:
    print(f"   ⏭️  Next run will resume from index {total_processed + 1}")
else:
    print(f"   ✅ All entries have been processed!")
print(f"{'='*70}")