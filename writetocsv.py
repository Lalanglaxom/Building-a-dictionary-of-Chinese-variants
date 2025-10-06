# Python
from bs4 import BeautifulSoup
import csv
import re
from pathlib import Path

HTML_PATH = r"E:\Benkyute Kudasai\Chinese\Building-a-dictionary-of-Chinese-variants\variants.html"
CSV_PATH = r"E:\Benkyute Kudasai\Chinese\Building-a-dictionary-of-Chinese-variants\variants_page_1.csv"

CTRL_RE = re.compile(r"[\x00-\x1F\x7F]")

def clean_text(s: str) -> str:
    if s is None:
        return ""
    # Replace control chars with tagged code, strip common nbsp
    s = CTRL_RE.sub(lambda m: f"[CTRL:U+{ord(m.group(0)):04X}]", s)
    return s.replace("\u00A0", " ").strip()

def td_text(td):
    # If there is an <img>, store its alt or src; else text
    img = td.find("img")
    if img:
        alt = img.get("alt") or ""
        src = img.get("src") or ""
        return f"[img:{alt}]" if alt else f"[img:{src}]"
    # Prefer <a> text if present
    a = td.find("a")
    if a:
        return clean_text(a.get_text())
    return clean_text(td.get_text())

def write_csv(html_path: str, csv_path: str) -> None:
    html = Path(html_path).read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    rows = []
    for tr in soup.select("div.appendV table tr[id^='av']"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        code = clean_text(tds[0].get_text())
        variant = td_text(tds[1])
        radical_stroke = clean_text(tds[2].get_text())
        # fourth td has 3 divs
        sub_divs = tds[3].find_all("div")
        standard = clean_text(sub_divs[0].get_text()) if len(sub_divs) > 0 else ""
        # Only the first 4 columns requested; keep to those
        rows.append([code, variant, radical_stroke, standard])

    # Write UTF-8 with BOM for Excel
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "variant", "radicalStroke", "standard"])
        w.writerows(rows)

if __name__ == "__main__":
    write_csv(HTML_PATH, CSV_PATH)
    print(f"Saved: {CSV_PATH}")
