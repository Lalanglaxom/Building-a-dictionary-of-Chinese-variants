# from bs4 import BeautifulSoup
# import sqlite3, os, time
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# import base64, os

# options = Options()
# options.add_argument("--headless=new")
# driver = webdriver.Chrome(options=options)

# conn = sqlite3.connect("dictionary.db")
# cur = conn.cursor()
# cur.execute("PRAGMA foreign_keys = ON;")
# cur.execute("""
# CREATE TABLE IF NOT EXISTS descriptions (
#     main_code TEXT PRIMARY KEY,
#     main_char TEXT,
#     shuo_wen TEXT,
#     appearance TEXT,
#     zhuyin TEXT,
#     pinyin TEXT,
#     meaning TEXT,
#     explanation TEXT,
#     FOREIGN KEY(main_code)
#         REFERENCES summary(code)
#         ON DELETE CASCADE
# );
# """)

# # pull a few test entries
# cur.execute("SELECT code, char, detail_url FROM summary LIMIT 5;")
# entries = cur.fetchall()

# def extract_td_text(td, code_prefix, folder="summary_images"):
#     """
#     Converts a <td> to plain text, saving inline <img> to PNG files.
#     Returns the text with placeholders like [img:path].
#     """
#     os.makedirs(folder, exist_ok=True)
#     text_parts = []
#     for elem in td.descendants:
#         if elem.name == "img" and elem.get("src", "").startswith("data:image"):
#             alt = elem.get("alt", "") or "[img]"
#             src = elem["src"]
#             try:
#                 _, b64data = src.split(",", 1)
#                 img_bytes = base64.b64decode(b64data)
#                 file_name = f"{code_prefix}_{len(os.listdir(folder))+1}.png"
#                 img_path  = os.path.join(folder, file_name)
#                 with open(img_path, "wb") as f:
#                     f.write(img_bytes)
#                 text_parts.append(f"[img:{img_path}]")
#             except Exception as e:
#                 text_parts.append("[img_error]")
#         elif elem.name is None:
#             text_parts.append(elem.strip())
#     return "".join(text_parts).strip()

# for i, (main_code, main_char, url) in enumerate(entries, 1):
#     print(f"[{i}] {main_char} → {url}")
#     driver.get(url)
#     WebDriverWait(driver, 10).until(
#         EC.presence_of_element_located((By.ID, "view"))
#     )

#     soup = BeautifulSoup(driver.page_source, "html.parser")

#     # --- find the <table id="view"> and collect information ---
#     table = soup.find("table", id="view")
#     if not table:
#         print(f"⚠️  No table for {main_char}")
#         continue

#     data = dict(main_code=main_code, main_char=main_char,
#                 shuo_wen=None, appearance=None,
#                 zhuyin=None, pinyin=None, meaning=None, explanation=None)

#     for row in table.find_all("tr"):
#         th = row.find("th")
#         td = row.find("td")
#         if not th or not td:
#             continue
#         title = th.get_text(strip=True)

#         if "說文釋形" in title:
#             data["shuo_wen"] = extract_td_text(td, main_code)
#         elif "字樣說明" in title:
#             data["appearance"] = extract_td_text(td, main_code)
#         elif "注" in title:
#             data["zhuyin"] = td.get_text(strip=True)
#         elif "漢語拼音" in title:
#             data["pinyin"] = td.get_text(strip=True)
#         elif "釋" in title:
#             data["meaning"] = extract_td_text(td, main_code)
#         elif "說明" in title:  # top-level general explanation
#             data["explanation"] = extract_td_text(td, main_code)

#     cur.execute("""
#         INSERT OR REPLACE INTO descriptions
#         (main_code, main_char, shuo_wen, appearance, zhuyin, pinyin, meaning, explanation)
#         VALUES (:main_code, :main_char, :shuo_wen, :appearance, :zhuyin, :pinyin, :meaning, :explanation)
#     """, data)
#     conn.commit()
#     print(f"✅ Saved description for {main_code}")
#     time.sleep(1.0)

# driver.quit()
# conn.close()
# print("✅ Finished summary crawling.")


