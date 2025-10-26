from bs4 import BeautifulSoup
import sqlite3, time, base64, os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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

# one table with all needed fields side‑by‑side
cur.execute("""
CREATE TABLE IF NOT EXISTS variant_descriptions (
    variant_code TEXT PRIMARY KEY,
    main_code TEXT,
    glyph_info TEXT,         -- combined “異體字” data
    description TEXT,        -- combined “內容” explanation
    zhuyin TEXT,
    pinyin TEXT,
    editor TEXT,
    FOREIGN KEY(main_code)
        REFERENCES summary(code)
        ON DELETE CASCADE
);
""")

# ---------- Load variant URLs ----------
cur.execute("SELECT variant_code, main_code, href FROM variants LIMIT 10;")
variants = cur.fetchall()
print(f"Total variant pages: {len(variants)}")


# ---------- Crawl each variant ----------
for i, (variant_code, main_code, url) in enumerate(variants, 1):
    print(f"[{i}] {variant_code} → {url}")
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

    glyph_info = zhuyin = pinyin = editor = description = None

    for row in table.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue
        label = th.get_text(strip=True)

        # ----- combine 「異體字」 data -----
        # normalize the label text: remove spaces
        label_clean = label.replace(" ", "")

        # ---- 異體字 row (variant identity) ----
        if "異體字" in label_clean:
            # <code> contains variant_code again
            code_tag = td.find("code")
            code_text = code_tag.get_text(strip=True) if code_tag else ""

            # glyph can be plain text or an <img> inside <big2>
            glyph = ""
            big2_tag = td.find("big2")
            if big2_tag:
                img = big2_tag.find("img")
                if img:
                    glyph = img.get("alt", "[img]")
                    # optional : also save the image itself
                    src = img.get("src", "")
                    if src.startswith("data:image"):
                        os.makedirs("variant_glyphs", exist_ok=True)
                        try:
                            _, b64 = src.split(",", 1)
                            glyph_bytes = base64.b64decode(b64)
                            g_path = os.path.join("variant_glyphs", f"{variant_code}.png")
                            with open(g_path, "wb") as f:
                                f.write(glyph_bytes)
                            glyph = f"[img:{g_path}]"
                        except Exception as e:
                            print(f"⚠️ error saving glyph image for {variant_code}: {e}")
                else:
                    glyph = big2_tag.get_text(strip=True)

            # radical‑stroke information usually comes after the glyph
            # grab the <td> text, split by spaces, and take the last token starting with a radical
            tail_text = td.get_text(" ", strip=True)
            # Example: "A00002-001 𠆤 人-01-03"
            radical = tail_text.split()[-1] if "‑" in tail_text or "-" in tail_text else ""

            glyph_info = " ".join(part for part in [code_text, glyph, radical] if part)

            # diagnostic print
            print(f"ℹ️ {variant_code}  →  glyph_info = {glyph_info}")
        # ----- 注音 / 拼音 / 研訂者 -----
        elif "注" in label:
            zhuyin = td.get_text(" ", strip=True)
        elif "漢語拼音" in label:
            pinyin = td.get_text(" ", strip=True)
        elif "研" in label:
            editor = td.get_text(" ", strip=True)

        # ----- 「內 容」 explanation -----
        elif "內" in label:
            description = extract_td_text(td, variant_code)

    # insert into DB
    cur.execute("""
        INSERT OR REPLACE INTO variant_descriptions
        (variant_code, main_code, glyph_info, description, zhuyin, pinyin, editor)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (variant_code, main_code, glyph_info, description, zhuyin, pinyin, editor))
    conn.commit()
    print(f"✅ Saved variant description for {variant_code}")
    time.sleep(1.0)

driver.quit()
conn.close()
print("✅ Finished crawling variant descriptions.")