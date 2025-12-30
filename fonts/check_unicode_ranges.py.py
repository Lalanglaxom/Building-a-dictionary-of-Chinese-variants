import sqlite3
import re
from collections import defaultdict

# Connect to your database
conn = sqlite3.connect("dictionary.db")
cur = conn.cursor()

# Get some variant characters
cur.execute("""
    SELECT variant_code, variant_char, img_path 
    FROM variants 
    WHERE variant_char IS NOT NULL 
    AND variant_char != '[img]' 
    AND variant_char != '[?]'
    AND length(variant_char) > 0
    LIMIT 100
""")

variants = cur.fetchall()

# Group characters by their Unicode range
unicode_ranges = defaultdict(list)

for variant_code, variant_char, img_path in variants:
    if not variant_char or len(variant_char.strip()) == 0:
        continue
    
    # Get first character
    char = variant_char.strip()[0]
    
    try:
        # Get Unicode codepoint
        codepoint = ord(char)
        hex_code = hex(codepoint)[2:].upper()
        
        # Determine which u****00.woff file it should belong to
        # Round down to nearest 0x100 (256) block
        block_start = (codepoint // 0x100) * 0x100
        font_file = f"u{hex(block_start)[2:].lower()}.woff"
        
        unicode_ranges[font_file].append({
            'variant_code': variant_code,
            'char': char,
            'codepoint': hex_code,
            'decimal': codepoint,
            'has_image': bool(img_path)
        })
        
    except Exception as e:
        print(f"Error processing {variant_char}: {e}")

# Print results
print("=" * 70)
print("UNICODE RANGE ANALYSIS")
print("=" * 70)

for font_file in sorted(unicode_ranges.keys()):
    chars = unicode_ranges[font_file]
    print(f"\n{font_file} ({len(chars)} characters)")
    print("-" * 70)
    
    # Show first 10 examples
    for item in chars[:10]:
        img_marker = "🖼️" if item['has_image'] else "  "
        print(f"  {img_marker} U+{item['codepoint']:>6} ({item['decimal']:>5}) '{item['char']}' - {item['variant_code']}")
    
    if len(chars) > 10:
        print(f"  ... and {len(chars) - 10} more")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total font files needed: {len(unicode_ranges)}")
print(f"Font files to download:")
for font_file in sorted(unicode_ranges.keys()):
    print(f"  - {font_file}")

conn.close()

# Test Theory: Check if u8000.woff would contain U+8000-U+80FF
print("\n" + "=" * 70)
print("THEORY CHECK: u8000.woff")
print("=" * 70)
print("Should contain characters in range: U+8000 - U+80FF")
print("Example characters in this range:")
for cp in range(0x8000, 0x8010):  # Just first 16 as example
    try:
        char = chr(cp)
        print(f"  U+{cp:04X} = '{char}'")
    except:
        print(f"  U+{cp:04X} = [invalid]")