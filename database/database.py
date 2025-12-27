import sqlite3

conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()
            
cur.execute("""
    CREATE TABLE supplementary_chars (
        main_char TEXT,
        supplementary_code TEXT,
        supplementary_char TEXT,
        appendix_id TEXT,
        appendix_name TEXT,
        appendix_link TEXT
)
""")

cur.execute("""
    CREATE TABLE appendix_details (
        supplementary_code TEXT,
        appendix_id TEXT,
        char_form TEXT,
        radical_stroke TEXT,
        pronunciation TEXT,
        word_examples TEXT,
        source_reference TEXT
)
""")

cur.execute("""
    CREATE TABLE variant_summary (
        main_code TEXT,
        variant_code TEXT,
        variant_char TEXT,
        radical_stroke TEXT,
        pronunciation_list TEXT
)
""")
