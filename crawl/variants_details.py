from bs4 import BeautifulSoup
import sqlite3, time, base64, os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ---------- Chinese to English Label Mapping ----------
LABEL_MAP = {
    "異體字": "variant_character",
    "內容": "content",
    "注音": "bopomofo",
    "漢語拼音": "pinyin",
    "研訂者": "researcher",
    "研訂說明": "research_notes_header",
}

def get_english_label(chinese_label):
    """Convert Chinese label to English."""
    clean = chinese_label.replace(" ", "").replace("　", "")
    for zh, en in LABEL_MAP.items():
        if zh in clean:
            return en
    return clean


# ---------- Helper: extract text + images ----------
def extract_td_text(td, file_prefix, folder="variant_desc_images"):
    os.makedirs(folder, exist_ok=True)
    parts = []
    for elem in td.descendants:
        if elem.name == "img" and elem.get("src", "").startswith("data:image"):
            try:
                _, b64 = elem["src"].split(",", 1)
                img_bytes = base64.b64decode(b64)
                fname = f"{file_prefix}_{len(os.listdir(folder))+1}.png"
                path = os.path.join(folder, fname)
                with open(path, "wb") as f:
                    f.write(img_bytes)
                parts.append(f"[img:{path}]")
            except Exception:
                parts.append("[img_error]")
        elif elem.name is None:
            parts.append(elem.strip())
    return "".join(parts).strip()


# ---------- Selenium setup ----------
options = Options()
options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)

# ---------- SQLite setup ----------
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

# ---------- Table structure matching HTML order ----------
cur.execute("""
CREATE TABLE IF NOT EXISTS variant_details (
    variant_code TEXT PRIMARY KEY,
    standard_code TEXT,
    
    -- 異體字 (variant_character): glyph + radical-stroke combined
    variant_character TEXT,
    
    -- 內容 (content - key references)
    key_references TEXT,
    
    -- 注音 (bopomofo)
    bopomofo TEXT,
    
    -- 漢語拼音 (pinyin)
    pinyin TEXT,
    
    -- 研訂者 (researcher)
    researcher TEXT,
    
    -- 內容 (content - explanation)
    explanation TEXT,
    
    -- Glyph image path
    glyph_image_path TEXT,
    
    FOREIGN KEY(standard_code) REFERENCES summary(code) ON DELETE CASCADE
);
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_variant_details_standard_code 
ON variant_details(standard_code);
""")

# ---------- Load variant URLs ----------
cur.execute("""
    SELECT variant_code, main_code, href 
    FROM variants 
    WHERE variant_code NOT IN (SELECT variant_code FROM variant_details);
""")
variants = cur.fetchall()
print(f"Total variant pages: {len(variants)}")


# ---------- Crawl each variant ----------
for i, (variant_code, main_code, url) in enumerate(variants, 1):
    print(f"\n[{i}] {variant_code} → {url}")
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "view"))
        )
    except Exception:
        print(f"⚠️ No table for {variant_code}")
        continue

    soup = BeautifulSoup(driver.page_source, "html.parser")
    table = soup.find("table", id="view")
    if not table:
        print(f"⚠️ Missing table on {variant_code}")
        continue

    # Initialize data
    data = {
        "variant_code": variant_code,
        "standard_code": main_code,
        "variant_character": None,
        "key_references": None,
        "bopomofo": None,
        "pinyin": None,
        "researcher": None,
        "explanation": None,
        "glyph_image_path": None,
    }

    passed_research_header = False

    for row in table.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        
        if not th:
            continue
            
        chinese_label = th.get_text(strip=True)
        english_label = get_english_label(chinese_label)
        
        print(f"   {chinese_label} → {english_label}")

        # 異體字 (variant_character)
        if english_label == "variant_character":
            glyph = ""
            radical_stroke = ""
            
            # Extract glyph from <big2>
            big2_tag = td.find("big2")
            if big2_tag:
                img = big2_tag.find("img")
                if img:
                    glyph = img.get("alt", "[img]")
                    # Save glyph image
                    src = img.get("src", "")
                    if src.startswith("data:image"):
                        os.makedirs("variant_glyphs", exist_ok=True)
                        try:
                            _, b64 = src.split(",", 1)
                            glyph_bytes = base64.b64decode(b64)
                            glyph_path = os.path.join("variant_glyphs", f"{variant_code}.png")
                            with open(glyph_path, "wb") as f:
                                f.write(glyph_bytes)
                            data["glyph_image_path"] = glyph_path
                        except Exception as e:
                            print(f"   ⚠️ Error saving glyph: {e}")
                else:
                    glyph = big2_tag.get_text(strip=True)
            
            # Extract radical-stroke (e.g., "一-04-05")
            tail_text = td.get_text(" ", strip=True)
            tokens = tail_text.split()
            for token in reversed(tokens):
                if "-" in token and any(c.isdigit() for c in token):
                    radical_stroke = token
                    break
            
            # Combine glyph + radical-stroke
            data["variant_character"] = f"{glyph} {radical_stroke}".strip()

        # 研訂說明 (section header)
        elif english_label == "research_notes_header":
            passed_research_header = True

        # 注音 (bopomofo)
        elif english_label == "bopomofo":
            data["bopomofo"] = td.get_text(" ", strip=True)

        # 漢語拼音 (pinyin)
        elif english_label == "pinyin":
            data["pinyin"] = td.get_text(" ", strip=True)

        # 研訂者 (researcher)
        elif english_label == "researcher":
            data["researcher"] = td.get_text(" ", strip=True)

        # 內容 (content)
        elif english_label == "content":
            if not passed_research_header:
                data["key_references"] = td.get_text(" ", strip=True)
            else:
                data["explanation"] = extract_td_text(td, variant_code)

    # Insert into DB
    cur.execute("""
        INSERT OR REPLACE INTO variant_details (
            variant_code, standard_code, variant_character,
            key_references, bopomofo, pinyin, researcher,
            explanation, glyph_image_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["variant_code"],
        data["standard_code"],
        data["variant_character"],
        data["key_references"],
        data["bopomofo"],
        data["pinyin"],
        data["researcher"],
        data["explanation"],
        data["glyph_image_path"],
    ))
    conn.commit()
    print(f"✅ Saved: {variant_code}")
    time.sleep(1.0)

driver.quit()
conn.close()
print("\n✅ Finished crawling variant descriptions.")