import sys
import sqlite3
import os
import re

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QScrollArea, QMessageBox, QTextEdit, QDialog)
from PyQt5.QtGui import QFont, QPixmap, QCursor, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
# Import the WebEngine widget for advanced font rendering
from PyQt5.QtWebEngineWidgets import QWebEngineView

# ═══════════════════════════════════════════════════════════════════════════
# 1. CONFIGURATION & OFFLINE FONT LOGIC
# ═══════════════════════════════════════════════════════════════════════════

DB = "dictionary.db"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(SCRIPT_DIR, "fonts")

# Standard fallback fonts for the rest of the UI
CHINESE_FALLBACK_FONTS = "'TW-Sung-Plus', 'SimSun', 'Microsoft YaHei', sans-serif"

def generate_offline_css():
    """
    This function scans your /fonts folder for files like 'u6100.ttf'.
    It creates a CSS rule for EACH file, mapping it to the specific Unicode range.
    This allows the WebEngine to load ONLY the correct font file from disk.
    """
    if not os.path.exists(FONT_DIR):
        print(f"Warning: Font directory not found at {FONT_DIR}")
        return ""

    css_rules = []
    
    # Loop through every file in the fonts folder
    for filename in os.listdir(FONT_DIR):
        # We look for files starting with 'u' (e.g., u6100.ttf or u28d00.woff)
        if filename.lower().startswith('u') and filename.lower().endswith(('.ttf', '.woff')):
            try:
                # Extract the hex code from filename (u6100 -> 6100)
                hex_str = filename[1:filename.find('.')]
                start_int = int(hex_str, 16)
                
                # MOE fonts usually cover a range of 256 characters (0xFF)
                end_int = start_int + 0xFF
                
                # Create file path compatible with CSS (forward slashes)
                file_path = os.path.join(FONT_DIR, filename).replace('\\', '/')
                
                # Create the @font-face rule
                rule = f"""
                @font-face {{
                    font-family: 'MOE-Offline';
                    src: url('file:///{file_path}') format('woff');
                    unicode-range: U+{start_int:x}-{end_int:x};
                }}
                """
                css_rules.append(rule)
            except ValueError:
                continue # Skip files that don't match the pattern

    return "\n".join(css_rules)

# Generate the Master CSS string once when the app starts
MASTER_CSS = generate_offline_css()

# ═══════════════════════════════════════════════════════════════════════════
# 2. HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def normalize_char(char):
    """Handle surrogate pairs for rare Chinese characters"""
    if not char:
        return ""
    try:
        char.encode('utf-8')
        return char
    except UnicodeEncodeError:
        try:
            return char.encode('utf-16', 'surrogatepass').decode('utf-16')
        except:
            return char

def resolve_image_path(img_path):
    """Finds the absolute path for images"""
    if not img_path:
        return None
    img_path = img_path.strip()
    
    # Check absolute path
    if os.path.isabs(img_path) and os.path.exists(img_path):
        return img_path
    
    # Check relative to script
    full_path = os.path.join(SCRIPT_DIR, img_path)
    if os.path.exists(full_path):
        return full_path
        
    return None

def format_text_with_images(text, section_type="default"):
    """Formats database text into HTML, replacing [img:...] tags"""
    if not text:
        return ""
        
    def replace_image(match):
        img_path = match.group(1).strip()
        resolved_path = resolve_image_path(img_path)
        if resolved_path:
            # WebEngine needs forward slashes for file:/// paths
            clean_path = resolved_path.replace('\\', '/')
            return f'<img src="file:///{clean_path}" style="max-height: 28px; vertical-align: middle; margin: 0 2px;">'
        return f'[img:{img_path}]'
    
    text = re.sub(r'img:([^$$]*?\.png)\]', replace_image, text)
    
    # Specific formatting for dictionary sections
    if section_type == "shuowen":
        text = re.sub(r'(段注本[：:])', r'<br>\1', text)
        text = re.sub(r'(?<!^)(大徐本[：:])', r'<br>\1', text)
    elif section_type == "style":
        text = re.sub(r'。\s*「', r'。<br>「', text)
    elif section_type == "definition":
        text = re.sub(r'(?<!^)(\d+\.)\s*', r'<br><br>\1 ', text)
    
    text = text.replace('\n', '<br>')
    return f'<html><body style="font-family:{CHINESE_FALLBACK_FONTS};font-size:14px;line-height:1.9;margin:0;padding:5px;">{text}</body></html>'

# ═══════════════════════════════════════════════════════════════════════════
# 3. DATABASE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_character_info(char):
    char = normalize_char(char)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code, char FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    conn.close()
    return row

def get_character_description(char):
    char = normalize_char(char)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    cur.execute("SELECT standard_character, shuowen_etymology, character_style, zhuyin_pronunciation, hanyu_pinyin, definition FROM descriptions WHERE main_code=?;", (row[0],))
    description = cur.fetchone()
    conn.close()
    return description

def get_variants(char):
    char = normalize_char(char)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return []
    cur.execute("SELECT variant_code, variant_char, img_path FROM variants WHERE main_code=? ORDER BY variant_code;", (row[0],))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_variant_details(variant_code):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT variant_code, standard_code, variant_character, key_references, 
               bopomofo, pinyin, researcher, explanation, glyph_image_path 
        FROM variant_details WHERE variant_code=?;
    """, (variant_code,))
    row = cur.fetchone()
    conn.close()
    return row

# ═══════════════════════════════════════════════════════════════════════════
# 4. CUSTOM UI WIDGETS
# ═══════════════════════════════════════════════════════════════════════════

class MainCharWebWidget(QWebEngineView):
    """
    A specialized Web Widget to display the Main Character.
    It uses the MASTER_CSS to load the correct uXXXX.ttf font from disk.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Make the background transparent so it looks like a label
        self.page().setBackgroundColor(Qt.transparent)
        self.setFixedSize(130, 130)  # Fixed size for the header area
        
    def load_char(self, char):
        """Generates HTML with our Custom CSS and loads it"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                /* Inject the massive CSS mapping we generated */
                {MASTER_CSS}
                
                body {{
                    background-color: transparent;
                    margin: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    overflow: hidden;
                }}
                .big-char {{
                    /* Priority: MOE-Offline (our local file) -> I.Ming -> System */
                    font-family: 'MOE-Offline', 'I.Ming', {CHINESE_FALLBACK_FONTS};
                    font-size: 80px;
                    color: #8B0000;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="big-char">{char}</div>
        </body>
        </html>
        """
        # Load the HTML, setting base URL to script dir for finding images if needed
        self.setHtml(html, QUrl.fromLocalFile(SCRIPT_DIR))


class SectionHeader(QFrame):
    """Red header bar for sections"""
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setFixedHeight(35)
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 0, 15, 0)
        
        # White accent line
        accent = QFrame()
        accent.setFixedSize(4, 20)
        accent.setStyleSheet("background:white;border:none;")
        layout.addWidget(accent)
        
        label = QLabel(text)
        label.setStyleSheet("color:white;font-size:14px;font-weight:bold;background:transparent;border:none;")
        layout.addWidget(label)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet("QFrame{background:#8B0000;border:none;}")


class TableRow(QFrame):
    """Two-column row for data display"""
    def __init__(self, label_text, has_top_accent=False, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        if has_top_accent:
            accent = QFrame()
            accent.setFixedHeight(3)
            accent.setStyleSheet("background:#8B0000;border:none;")
            main_layout.addWidget(accent)
            
        row_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Left Label
        self.label_frame = QFrame()
        self.label_frame.setFixedWidth(100)
        self.label_frame.setStyleSheet("QFrame{background:#F5F5F0;border:1px solid #CCC;border-right:none;}")
        label_layout = QVBoxLayout()
        label_layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size:13px;font-weight:bold;color:#333;background:transparent;border:none;")
        label.setWordWrap(True)
        label_layout.addWidget(label)
        self.label_frame.setLayout(label_layout)
        layout.addWidget(self.label_frame)
        
        # Right Content
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("QFrame{background:white;border:1px solid #CCC;}")
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(10, 8, 10, 8)
        self.content_frame.setLayout(self.content_layout)
        layout.addWidget(self.content_frame, 1)
        
        row_widget.setLayout(layout)
        main_layout.addWidget(row_widget)
        self.setLayout(main_layout)
    
    def set_html_content(self, html, min_height=60):
        self.clear_content()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(html)
        # Use fallback fonts for the text description areas
        text_edit.setStyleSheet(f"QTextEdit{{font-family:{CHINESE_FALLBACK_FONTS};font-size:14px;color:#333;background:white;border:none;}}")
        text_edit.setMinimumHeight(min_height)
        self.content_layout.addWidget(text_edit)
    
    def add_text_label(self, text, size=14):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-family:{CHINESE_FALLBACK_FONTS};font-size:{size}px;color:#333;background:transparent;border:none;")
        lbl.setWordWrap(True)
        self.content_layout.addWidget(lbl)

    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class VariantCharacterBox(QFrame):
    """Clickable box for variants"""
    clicked = pyqtSignal(object)
    
    def __init__(self, char="", code="", img_path="", variant_code="", parent=None):
        super().__init__(parent)
        self.char = char
        self.code = code
        self.variant_code = variant_code
        self.is_selected = False
        
        self.setFixedSize(70, 75)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        
        # Top Code Label
        self.code_label = QLabel(code)
        self.code_label.setAlignment(Qt.AlignCenter)
        self.code_label.setFixedHeight(15)
        self.code_label.setStyleSheet("color:#666;font-size:9px;")
        layout.addWidget(self.code_label)
        
        # Character or Image Display
        resolved_img_path = resolve_image_path(img_path) if img_path else None
        self.char_label = QLabel()
        self.char_label.setAlignment(Qt.AlignCenter)
        
        if resolved_img_path:
            pixmap = QPixmap(resolved_img_path)
            if not pixmap.isNull():
                self.char_label.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.char_label.setText(char or "?")
                self.char_label.setStyleSheet(f"font-family:{CHINESE_FALLBACK_FONTS};font-size:26px;")
            self.is_image = True
        else:
            self.char_label.setText(char or "")
            self.char_label.setStyleSheet(f"font-family:{CHINESE_FALLBACK_FONTS};font-size:26px;")
            self.is_image = False
        
        layout.addWidget(self.char_label, 1)
        self.setLayout(layout)
        self.update_style()
    
    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("VariantCharacterBox{background:#8B0000;border:1px solid #600000;}")
            self.code_label.setStyleSheet("color:white;background:transparent;border:none;font-size:9px;")
            self.char_label.setStyleSheet(f"color:{'transparent' if self.is_image else 'white'};background:transparent;border:none;")
        else:
            self.setStyleSheet("VariantCharacterBox{background:white;border:1px solid #999;}VariantCharacterBox:hover{border:2px solid #8B0000;}")
            self.code_label.setStyleSheet("color:#666;background:transparent;border:none;font-size:9px;")
            self.char_label.setStyleSheet("color:#333;background:transparent;border:none;")
    
    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)


class VariantDetailWindow(QDialog):
    """Popup window for variant details"""
    def __init__(self, variant_code, parent=None):
        super().__init__(parent)
        self.variant_code = variant_code
        self.setWindowTitle(f'Variant Details - {variant_code}')
        self.setGeometry(150, 150, 800, 700)
        self.setStyleSheet("background-color: #E8D4C8;")
        self.initUI()
    
    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background-color:#E8D4C8;}")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #E8D4C8;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Header
        content_layout.addWidget(SectionHeader("Description"))
        
        details = get_variant_details(self.variant_code)
        
        if details:
            variant_code, standard_code, variant_char, key_refs, bopomofo, pinyin, researcher, explanation, glyph_path = details
            
            # Row 1: Character Info
            row1 = TableRow("Variant\nCharacter")
            row1_layout = row1.label_frame.parentWidget().layout().itemAt(1).widget().layout() # Access content layout
            
            # We create a horizontal box for the character info inside the row
            h_box = QWidget()
            h_lay = QHBoxLayout()
            h_lay.setContentsMargins(0,0,0,0)
            
            code_label = QLabel(f"[{variant_code}]")
            code_label.setStyleSheet(f"font-family:{CHINESE_FALLBACK_FONTS};font-size:16px;color:#333;")
            h_lay.addWidget(code_label)
            
            resolved_glyph = resolve_image_path(glyph_path) if glyph_path else None
            if resolved_glyph:
                glyph_label = QLabel()
                glyph_label.setPixmap(QPixmap(resolved_glyph).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                h_lay.addWidget(glyph_label)
            
            if variant_char:
                char_label = QLabel(variant_char)
                char_label.setStyleSheet(f"font-family:{CHINESE_FALLBACK_FONTS};font-size:14px;color:#333;")
                h_lay.addWidget(char_label)
                
            h_lay.addStretch()
            h_box.setLayout(h_lay)
            
            # We add this custom widget to the table row's content area
            row1.clear_content() # Clear init default
            row1.content_layout.addWidget(h_box)
            content_layout.addWidget(row1)
            
            # Row 2: Content
            row2 = TableRow("Content")
            if key_refs:
                html = format_text_with_images(key_refs, "default")
                row2.set_html_content(html, 80)
            else:
                row2.add_text_label("No data available")
            content_layout.addWidget(row2)
            
            # Research Notes Section
            has_research = any([bopomofo, pinyin, researcher, explanation])
            if has_research:
                content_layout.addWidget(SectionHeader("Research Notes"))
                
                if bopomofo:
                    r = TableRow("Bopomofo")
                    r.add_text_label(bopomofo, 24)
                    content_layout.addWidget(r)
                
                if pinyin:
                    r = TableRow("Hanyu\nPinyin")
                    r.add_text_label(pinyin, 16)
                    content_layout.addWidget(r)
                    
                if researcher:
                    r = TableRow("Researcher")
                    r.add_text_label(researcher, 14)
                    content_layout.addWidget(r)
                    
                if explanation:
                    r = TableRow("Content", has_top_accent=True)
                    html = format_text_with_images(explanation, "default")
                    r.set_html_content(html, 150)
                    content_layout.addWidget(r)
        
        # Close Button
        btn_frame = QFrame()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 15, 20, 15)
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("QPushButton{background:#666;color:white;border:none;border-radius:5px;padding:8px 25px;font-size:13px;}QPushButton:hover{background:#888;}")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        btn_frame.setLayout(btn_layout)
        content_layout.addWidget(btn_frame)
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

# ═══════════════════════════════════════════════════════════════════════════
# 5. MAIN WINDOW APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

class CharacterDictionary(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_char = ""
        self.variant_boxes = []
        self.selected_variant_box = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Chinese Character Dictionary')
        self.setGeometry(100, 100, 1000, 900)
        
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #E8D4C8;")
        self.setCentralWidget(main_widget)
        
        # Main Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background-color:#E8D4C8;}")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #E8D4C8;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)
        
        # --- HEADER AREA ---
        header = QFrame()
        header.setStyleSheet("background:transparent;")
        h_layout = QHBoxLayout()
        
        self.code_label = QLabel("")
        self.code_label.setStyleSheet("font-size:18px;font-weight:bold;color:#333;background:transparent;")
        h_layout.addWidget(self.code_label)
        
        # ** KEY CHANGE: Using Web Engine for the Main Character **
        self.main_char_web_view = MainCharWebWidget()
        h_layout.addWidget(self.main_char_web_view)
        
        self.stroke_label = QLabel("")
        self.stroke_label.setStyleSheet("font-size:14px;color:#666;background:transparent;")
        h_layout.addWidget(self.stroke_label)
        
        h_layout.addStretch()
        header.setLayout(h_layout)
        content_layout.addWidget(header)
        content_layout.addSpacing(20)
        
        # --- INPUT AREA ---
        input_frame = QFrame()
        input_frame.setStyleSheet("QFrame{background:white;border:1px solid #DDD;border-radius:5px;}")
        i_layout = QHBoxLayout()
        i_layout.setContentsMargins(15, 10, 15, 10)
        
        i_layout.addWidget(QLabel("Enter Character:", styleSheet="border:none;"))
        
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type char...")
        self.entry.setMaxLength(2)
        self.entry.setFixedWidth(150)
        self.entry.setStyleSheet(f"font-size:24px;padding:5px;border:2px solid #8B0000;border-radius:5px;font-family:{CHINESE_FALLBACK_FONTS};")
        self.entry.returnPressed.connect(self.search_character)
        i_layout.addWidget(self.entry)
        
        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("QPushButton{background:#8B0000;color:white;border:none;border-radius:5px;padding:8px 20px;font-weight:bold;}")
        search_btn.clicked.connect(self.search_character)
        i_layout.addWidget(search_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("QPushButton{background:#666;color:white;border:none;border-radius:5px;padding:8px 20px;}")
        clear_btn.clicked.connect(self.clear_all)
        i_layout.addWidget(clear_btn)
        
        i_layout.addStretch()
        input_frame.setLayout(i_layout)
        content_layout.addWidget(input_frame)
        content_layout.addSpacing(15)
        
        # --- VARIANTS AREA ---
        content_layout.addWidget(SectionHeader("Variants"))
        
        self.variants_container = QFrame()
        self.variants_container.setStyleSheet("QFrame{background:#F8F8F5;border:1px solid #DDD;border-top:none;}")
        
        self.variants_scroll = QScrollArea()
        self.variants_scroll.setWidgetResizable(True)
        self.variants_scroll.setFixedHeight(100)
        self.variants_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        
        self.variants_widget = QWidget()
        self.variants_layout = QHBoxLayout()
        self.variants_layout.setContentsMargins(15, 10, 15, 10)
        self.variants_layout.setSpacing(8)
        self.variants_layout.setAlignment(Qt.AlignLeft)
        self.variants_widget.setLayout(self.variants_layout)
        
        self.variants_scroll.setWidget(self.variants_widget)
        
        c_layout = QVBoxLayout()
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.addWidget(self.variants_scroll)
        self.variants_container.setLayout(c_layout)
        content_layout.addWidget(self.variants_container)
        content_layout.addSpacing(15)
        
        # --- DESCRIPTION AREA ---
        content_layout.addWidget(SectionHeader("Description"))
        
        self.rows = [
            TableRow("Standard\nCharacter"),
            TableRow("Shuowen\nEtymology"),
            TableRow("Character\nStyle"),
            TableRow("Zhuyin"),
            TableRow("Hanyu\nPinyin"),
            TableRow("Definition", has_top_accent=True) # Definition usually last
        ]
        
        for row in self.rows:
            content_layout.addWidget(row)
            
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        main_widget.setLayout(main_layout)

    def on_variant_clicked(self, box):
        if self.selected_variant_box:
            self.selected_variant_box.set_selected(False)
        box.set_selected(True)
        self.selected_variant_box = box
        
        if box.variant_code:
            detail_window = VariantDetailWindow(box.variant_code, self)
            detail_window.show()

    def clear_variants_display(self):
        for box in self.variant_boxes:
            try: box.clicked.disconnect()
            except: pass
            box.deleteLater()
        self.variant_boxes.clear()
        self.selected_variant_box = None
        
        # Clear layout items
        while self.variants_layout.count():
            item = self.variants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def update_variants_display(self, char):
        self.clear_variants_display()
        variants = get_variants(char)
        
        if not variants:
            no_variants_label = QLabel("No variants found for this character")
            no_variants_label.setStyleSheet("color:#999;font-size:14px;font-style:italic;padding:10px;")
            self.variants_layout.addWidget(no_variants_label)
            self.variants_layout.addStretch()
            return
            
        for variant_code, variant_char, img_path in variants:
            suffix = f".{variant_code.split('-')[-1]}" if variant_code and '-' in variant_code else ""
            box = VariantCharacterBox(
                (variant_char or "").strip(), 
                suffix, 
                (img_path or "").strip(),
                variant_code
            )
            box.clicked.connect(self.on_variant_clicked)
            self.variants_layout.addWidget(box)
            self.variant_boxes.append(box)
        
        self.variants_layout.addStretch()

    def get_first_character(self, text):
        if not text: return ""
        text = normalize_char(text)
        if len(text) >= 2:
            # Check for surrogate pair range
            if 0xD800 <= ord(text[0]) <= 0xDBFF:
                return text[:2]
        return text[0]

    def search_character(self):
        raw_text = self.entry.text().strip()
        if not raw_text:
            QMessageBox.warning(self, "Input Error", "Please enter a character.")
            return
        
        char = self.get_first_character(raw_text)
        char = normalize_char(char)
        
        char_info = get_character_info(char)
        if not char_info:
            QMessageBox.information(self, "Not Found", f"No information found for '{char}'.")
            return
        
        code, main_char = char_info
        
        # Update Basic Info
        self.code_label.setText(code)
        self.stroke_label.setText("--05-06")
        
        # ** KEY CHANGE: Load main char into WebEngine **
        self.main_char_web_view.load_char(main_char)
        
        # Update Variants
        self.update_variants_display(char)
        
        # Update Description Rows
        description = get_character_description(char)
        if not description:
            for row in self.rows:
                row.clear_content()
            return
            
        standard_char, shuowen, char_style, zhuyin, pinyin, definition = description
        
        # Map data to rows
        data_map = [
            (f"[{code}] {main_char} --05-06", 18, None), # Standard
            (shuowen, None, "shuowen"),                  # Shuowen
            (char_style, None, "style"),                 # Style
            (zhuyin, 24, None),                          # Zhuyin
            (pinyin, 16, None),                          # Pinyin
            (definition, None, "definition")             # Definition
        ]
        
        for i, (text, font_size, section) in enumerate(data_map):
            if section:
                # Render HTML content
                html = format_text_with_images(text or "", section)
                # Definition gets more height
                min_h = 200 if section == "definition" else 80
                self.rows[i].set_html_content(html, min_h)
            else:
                # Render Simple Text
                self.rows[i].clear_content()
                self.rows[i].add_text_label(text or "No data", font_size or 14)

    def clear_all(self):
        self.entry.clear()
        self.code_label.setText("")
        # Clear Web View
        self.main_char_web_view.setHtml("")
        self.stroke_label.setText("")
        
        for row in self.rows:
            row.clear_content()
            
        self.clear_variants_display()
        self.entry.setFocus()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = CharacterDictionary()
    window.show()
    sys.exit(app.exec_())