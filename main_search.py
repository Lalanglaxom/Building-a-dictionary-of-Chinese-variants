import sys
import sqlite3
import os
import re
import webbrowser

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QScrollArea, QMessageBox, QTextEdit, QDialog,
                             QTabWidget)
from PyQt5.QtGui import QFont, QPixmap, QCursor
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Try to import fontTools
try:
    from fontTools.ttLib import TTFont
    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False
    print("WARNING: 'fonttools' not found. Install with: pip install fonttools")

# ═══════════════════════════════════════════════════════════════════════════
# 1. CONFIGURATION & FONT MANAGER
# ═══════════════════════════════════════════════════════════════════════════

DB = "dictionary.db"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(SCRIPT_DIR, "fonts")
DEFAULT_FONTS = "sans-serif, 'Microsoft YaHei', 'SimSun'"

class FontManager:
    def __init__(self):
        self.css_rules = []
        self.font_families = []
        self.char_map = {}
        self.scan_fonts()

    def scan_fonts(self):
        if not os.path.exists(FONT_DIR):
            os.makedirs(FONT_DIR)
            return

        files = sorted([f for f in os.listdir(FONT_DIR) if f.lower().endswith(('.woff', '.ttf'))])
        
        for filename in files:
            file_path = os.path.join(FONT_DIR, filename).replace('\\', '/')
            safe_name = filename.replace(".", "_").replace("-", "_")
            family_name = f"Font_{safe_name}"
            
            rule = f"@font-face {{ font-family: '{family_name}'; src: url('file:///{file_path}'); }}"
            self.css_rules.append(rule)
            self.font_families.append(f"'{family_name}'")

            if HAS_FONTTOOLS:
                full_path = os.path.join(FONT_DIR, filename)
                try:
                    tt = TTFont(full_path)
                    cmap = tt.getBestCmap()
                    if cmap:
                        for char_code in cmap:
                            if char_code not in self.char_map:
                                self.char_map[char_code] = {
                                    'file': filename,
                                    'family': family_name,
                                    'path': file_path
                                }
                    tt.close()
                except Exception as e:
                    print(f"Error reading font {filename}: {e}")

    def get_font_data_for_char(self, char_str):
        if not char_str:
            return "", DEFAULT_FONTS

        if HAS_FONTTOOLS and char_str:
            code_point = ord(char_str[0])
            if code_point in self.char_map:
                data = self.char_map[code_point]
                css = f"@font-face {{ font-family: '{data['family']}'; src: url('file:///{data['path']}'); }}"
                stack = f"'{data['family']}', {DEFAULT_FONTS}"
                return css, stack
        
        full_css = "".join(self.css_rules)
        full_stack = ", ".join(self.font_families) + ", " + DEFAULT_FONTS
        return full_css, full_stack

font_manager = FontManager()

# ═══════════════════════════════════════════════════════════════════════════
# 2. DATABASE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def normalize_char(char):
    if not char: return ""
    return char

def resolve_image_path(img_path):
    if not img_path: return None
    img_path = img_path.strip()
    if os.path.isabs(img_path) and os.path.exists(img_path): return img_path
    full_path = os.path.join(SCRIPT_DIR, img_path)
    if os.path.exists(full_path): return full_path
    return None

def format_text_with_images(text, section_type="default", extra_css="", font_stack=DEFAULT_FONTS):
    if not text: return ""
    
    def replace_image(match):
        img_path = match.group(1).strip()
        resolved_path = resolve_image_path(img_path)
        if resolved_path:
            clean_path = resolved_path.replace('\\', '/')
            return f'<img src="file:///{clean_path}" style="max-height: 28px; vertical-align: middle; margin: 0 2px;">'
        return f'[img:{img_path}]'
    
    text = re.sub(r'img:([^$]*?\.png)\]', replace_image, text)
    if section_type == "definition":
        text = re.sub(r'(?<!^)(\d+\.)\s*', r'<br><br>\1 ', text)
    
    text = text.replace('\n', '<br>')
    
    return f"""
    <html>
    <head>
        <style>
            {extra_css}
            body {{
                font-family: {font_stack};
                font-size: 14px;
                line-height: 1.9;
                margin: 0;
                padding: 5px;
                color: #333;
            }}
        </style>
    </head>
    <body>{text}</body>
    </html>
    """

def extract_code_from_text(full_text):
    """Extract code like A03410-003 from text like '丹A03410-003U+4E39丶-內 4'"""
    # Match pattern: uppercase letter followed by digits, hyphen, digits
    match = re.search(r'([A-Z]\d{5}-\d{3})', full_text)
    if match:
        return match.group(1)
    return None

def get_search_results(search_char):
    """Get search results for a character"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT result_char, result_code, ucs_code, radical_stroke, detail_url, data_sn, icon_label
        FROM search_results
        WHERE search_char = ? AND result_type = 'Text'
        ORDER BY result_code
    """, (search_char,))
    text_results = cur.fetchall()
    
    cur.execute("""
        SELECT result_char, icon_label, ucs_code, radical_stroke, detail_url, appendix_id, anchor_id
        FROM search_results
        WHERE search_char = ? AND result_type = 'Appendix'
        ORDER BY icon_label
    """, (search_char,))
    appendix_results = cur.fetchall()
    
    conn.close()
    return text_results, appendix_results

def get_character_info(char):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code, char FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    conn.close()
    return row

def get_character_by_code(code):
    """Get character info by code from summary table"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code, char FROM summary WHERE code=?;", (code,))
    row = cur.fetchone()
    conn.close()
    return row

def find_main_code_from_variant(code):
    """Find main code if the code is a variant"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT main_code FROM variants WHERE variant_code=?;", (code,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

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
# 3. SEARCH RESULT BOX
# ═══════════════════════════════════════════════════════════════════════════

class SearchResultBox(QFrame):
    """Clickable box for search result"""
    clicked = pyqtSignal(str, str)  # Emits (full_text, ucs_code)
    
    def __init__(self, alter_char="",char="", bottom_label="", ucs_code="", icon_label="", full_text="", parent=None):
        super().__init__(parent)
        self.alter_char = char
        self.char = alter_char
        self.bottom_label = bottom_label
        self.ucs_code = ucs_code
        self.icon_label = icon_label
        self.full_text = full_text
        
        self.setFixedSize(100, 110)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Character display
        self.char_view = QWebEngineView()
        self.char_view.setFixedSize(90, 70)
        self.char_view.page().setBackgroundColor(Qt.white)
        self.char_view.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        custom_css, font_stack = font_manager.get_font_data_for_char(char)
        char_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                {custom_css}
                html, body {{
                    margin: 0; padding: 0;
                    width: 100%; height: 100%;
                    background: white;
                    overflow: hidden;
                }}
                body {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    position: relative;
                }}
                .char {{
                    font-family: {font_stack};
                    font-size: 48px;
                    color: #333;
                    line-height: 1;
                }}
                .icon {{
                    position: absolute;
                    bottom: 2px;
                    left: 2px;
                    background: #8B0000;
                    color: white;
                    font-size: 9px;
                    padding: 2px 4px;
                    border-radius: 2px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="char">{alter_char}</div>
            {f'<div class="icon">{icon_label}</div>' if icon_label else ''}
        </body>
        </html>
        """
        self.char_view.setHtml(char_html, QUrl.fromLocalFile(SCRIPT_DIR))
        layout.addWidget(self.char_view, 1)
        
        # Bottom label
        self.label = QLabel(bottom_label)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                background: #8B0000;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 3px;
                border-radius: 3px;
            }
        """)
        self.label.setFixedHeight(20)
        # layout.addWidget(self.label)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            SearchResultBox {
                background: white;
                border: 2px solid #DDD;
                border-radius: 5px;
            }
            SearchResultBox:hover {
                border: 2px solid #8B0000;
                background: #FFF8F8;
            }
        """)
        
        # Tooltip only shows if UCS code exists
        if ucs_code:
            # print(char)
            self.setToolTip(f"{char}\n{ucs_code}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.full_text, self.ucs_code)
        super().mousePressEvent(event)

# ═══════════════════════════════════════════════════════════════════════════
# 4. CHARACTER DESCRIPTION WINDOW (from description.py logic)
# ═══════════════════════════════════════════════════════════════════════════

class SectionHeader(QFrame):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setFixedHeight(35)
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 0, 15, 0)
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
        
        self.label_frame = QFrame()
        self.label_frame.setFixedWidth(100)
        self.label_frame.setStyleSheet("QFrame{background:#F5F5F0;border:1px solid #CCC;border-right:none;}")
        l_layout = QVBoxLayout()
        l_layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size:13px;font-weight:bold;color:#333;")
        label.setWordWrap(True)
        l_layout.addWidget(label)
        self.label_frame.setLayout(l_layout)
        layout.addWidget(self.label_frame)
        
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
        text_edit.setStyleSheet("QTextEdit{background:white;border:none;}")
        text_edit.setMinimumHeight(min_height)
        self.content_layout.addWidget(text_edit)

    def add_text_label(self, text, size=14):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-family:{DEFAULT_FONTS};font-size:{size}px;color:#333;background:transparent;border:none;")
        lbl.setWordWrap(True)
        self.content_layout.addWidget(lbl)

    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

class VariantCharacterBox(QFrame):
    """Variant box widget"""
    clicked = pyqtSignal(object)
    
    def __init__(self, char="", code="", img_path="", variant_code="", parent=None):
        super().__init__(parent)
        self.char = char
        self.code = code
        self.variant_code = variant_code
        self.img_path = img_path
        self.is_selected = False
        
        self.setFixedSize(80, 90)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        
        self.code_label = QLabel(code)
        self.code_label.setAlignment(Qt.AlignCenter)
        self.code_label.setFixedHeight(15)
        self.code_label.setStyleSheet("color:#666;font-size:10px;")
        layout.addWidget(self.code_label)
        
        resolved_img_path = resolve_image_path(img_path) if img_path else None
        
        if resolved_img_path:
            self.is_image = True
            self.char_widget = QLabel()
            self.char_widget.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(resolved_img_path)
            if not pixmap.isNull():
                self.char_widget.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.char_widget.setText("Img Error")
        else:
            self.is_image = False
            self.char_widget = QWebEngineView()
            self.char_widget.page().setBackgroundColor(Qt.transparent)
            self.char_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.render_char_html(text_color="#333")

        layout.addWidget(self.char_widget, 1)
        self.setLayout(layout)
        self.update_style()
    
    def render_char_html(self, text_color="#333"):
        if self.is_image: return
        char_to_show = self.char or ""
        custom_css, font_family = font_manager.get_font_data_for_char(char_to_show)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                {custom_css}
                body {{
                    background: transparent;
                    margin: 0; padding: 0;
                    display: flex; justify-content: center; align-items: center;
                    height: 100vh; overflow: hidden;
                }}
                .char {{
                    font-family: {font_family}; 
                    font-size: 36px;
                    color: {text_color};
                    line-height: 1;
                }}
            </style>
        </head>
        <body><div class="char">{char_to_show}</div></body>
        </html>
        """
        self.char_widget.setHtml(html, QUrl.fromLocalFile(SCRIPT_DIR))

    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("VariantCharacterBox{background:#8B0000;border:2px solid #600000;}")
            self.code_label.setStyleSheet("color:white;background:transparent;border:none;font-size:10px;")
            if not self.is_image: self.render_char_html(text_color="white")
        else:
            self.setStyleSheet("VariantCharacterBox{background:white;border:1px solid #999;}VariantCharacterBox:hover{border:2px solid #8B0000;}")
            self.code_label.setStyleSheet("color:#666;background:transparent;border:none;font-size:10px;")
            if not self.is_image: self.render_char_html(text_color="#333")
    
    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)

class VariantDetailWindow(QDialog):
    """Variant detail window"""
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
        
        content_layout.addWidget(SectionHeader("Description"))
        
        details = get_variant_details(self.variant_code)
        if details:
            variant_code, standard_code, variant_char, key_refs, bopomofo, pinyin, researcher, explanation, glyph_path = details
            
            custom_css, custom_stack = font_manager.get_font_data_for_char(variant_char or "")

            row1 = TableRow("Variant\nCharacter")
            h_box = QWidget()
            h_lay = QHBoxLayout()
            h_lay.setContentsMargins(0,0,0,0)
            h_lay.setSpacing(20)
            
            code_label = QLabel(f"[{variant_code}]")
            code_label.setStyleSheet(f"font-size:24px;font-weight:bold;color:#555;")
            h_lay.addWidget(code_label)
            
            resolved_glyph = resolve_image_path(glyph_path) if glyph_path else None
            if resolved_glyph:
                glyph_label = QLabel()
                glyph_label.setPixmap(QPixmap(resolved_glyph).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                h_lay.addWidget(glyph_label)
            
            if variant_char:
                char_view = QWebEngineView()
                char_view.setFixedSize(150, 100)
                char_view.page().setBackgroundColor(Qt.transparent)
                char_view.setAttribute(Qt.WA_TransparentForMouseEvents)
                
                char_html = f"""
                <html>
                <head>
                    <style>
                        {custom_css}
                        html, body {{
                            margin: 0; padding: 0; width: 100%; height: 100%;
                            background: transparent; overflow: hidden;
                        }}
                        body {{
                            display: flex;
                            justify-content: center;
                            align-items: center;
                        }}
                        .v {{ 
                            font-family: {custom_stack}; 
                            font-size: 24px; 
                            color: #8B0000; 
                            font-weight: bold;
                            line-height: 1;
                        }}
                    </style>
                </head>
                <body>
                    <div class="v">{variant_char}</div>
                </body>
                </html>
                """
                char_view.setHtml(char_html, QUrl.fromLocalFile(SCRIPT_DIR))
                h_lay.addWidget(char_view)
            
            h_lay.addStretch()
            h_box.setLayout(h_lay)
            row1.clear_content()
            row1.content_layout.addWidget(h_box)
            content_layout.addWidget(row1)
            
            row2 = TableRow("Content")
            if key_refs: 
                html = format_text_with_images(key_refs, "default", custom_css, custom_stack)
                row2.set_html_content(html, 80)
            else: 
                row2.add_text_label("No data available")
            content_layout.addWidget(row2)
            
            if any([bopomofo, pinyin, researcher, explanation]):
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
                    html = format_text_with_images(explanation, "default", custom_css, custom_stack)
                    r.set_html_content(html, 150)
                    content_layout.addWidget(r)
        
        btn_frame = QFrame()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 15, 20, 15)
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("QPushButton{background:#666;color:white;border:none;border-radius:5px;padding:8px 25px;}")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        btn_frame.setLayout(btn_layout)
        content_layout.addWidget(btn_frame)
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

class CharacterDescriptionWindow(QDialog):
    """Window to show full character description (like description.py)"""
    def __init__(self, char, code, parent=None):
        super().__init__(parent)
        self.char = char
        self.code = code
        self.setWindowTitle(f'Character Details - {char}')
        self.setGeometry(100, 100, 1000, 900)
        self.setStyleSheet("background-color: #E8D4C8;")
        self.variant_boxes = []
        self.selected_variant_box = None
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
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background:transparent;")
        h_layout = QHBoxLayout()
        
        code_label = QLabel(self.code)
        code_label.setStyleSheet("font-size:18px;font-weight:bold;color:#333;")
        h_layout.addWidget(code_label)
        
        main_char_label = QLabel(self.char)
        main_char_label.setStyleSheet(f"font-size:100px;color:#8B0000;font-weight:bold;font-family:{DEFAULT_FONTS};")
        h_layout.addWidget(main_char_label)
        
        stroke_label = QLabel("--05-06")
        stroke_label.setStyleSheet("font-size:14px;color:#666;")
        h_layout.addWidget(stroke_label)
        h_layout.addStretch()
        
        header.setLayout(h_layout)
        content_layout.addWidget(header)
        content_layout.addSpacing(20)
        
        # Variants
        content_layout.addWidget(SectionHeader("Variants"))
        self.variants_container = QFrame()
        self.variants_container.setStyleSheet("QFrame{background:#F8F8F5;border:1px solid #DDD;border-top:none;}")
        self.variants_scroll = QScrollArea()
        self.variants_scroll.setWidgetResizable(True)
        self.variants_scroll.setFixedHeight(120)
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

        # Populate Variants
        self.update_variants_display()

        # Description Section
        content_layout.addWidget(SectionHeader("Description"))
        
        description = get_character_description(self.char)
        
        # Prepare rows
        self.rows = [
            TableRow("Standard\nCharacter"),
            TableRow("Shuowen\nEtymology"),
            TableRow("Character\nStyle"),
            TableRow("Zhuyin"),
            TableRow("Hanyu\nPinyin"),
            TableRow("Definition", has_top_accent=True)
        ]
        
        for row in self.rows:
            content_layout.addWidget(row)

        if description:
            standard_char, shuowen, char_style, zhuyin, pinyin, definition = description
            
            # Helper to set content
            def set_row_data(row_index, text, section_type=None):
                if text:
                    if section_type:
                        html = format_text_with_images(text, section_type)
                        min_h = 200 if section_type == "definition" else 80
                        self.rows[row_index].set_html_content(html, min_h)
                    else:
                        self.rows[row_index].add_text_label(text)
                else:
                    self.rows[row_index].add_text_label("No data")

            # Row 0: Standard Char (Just text for now)
            self.rows[0].add_text_label(f"[{self.code}] {self.char}")
            
            # Row 1: Shuowen
            set_row_data(1, shuowen, "shuowen")
            
            # Row 2: Style
            set_row_data(2, char_style, "style")
            
            # Row 3: Zhuyin
            if zhuyin: self.rows[3].add_text_label(zhuyin, 24)
            else: self.rows[3].add_text_label("No data")
            
            # Row 4: Pinyin
            if pinyin: self.rows[4].add_text_label(pinyin, 16)
            else: self.rows[4].add_text_label("No data")
            
            # Row 5: Definition
            set_row_data(5, definition, "definition")

        else:
            for row in self.rows:
                row.add_text_label("No Data Found")

        content_layout.addStretch()
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # Close Button Area
        btn_frame = QFrame()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 10, 20, 10)
        btn_layout.addStretch()
        close_btn = QPushButton("Close Window")
        close_btn.setStyleSheet("QPushButton{background:#666;color:white;border:none;border-radius:5px;padding:10px 30px;font-weight:bold;}")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        btn_frame.setLayout(btn_layout)
        main_layout.addWidget(btn_frame)

        self.setLayout(main_layout)

    def on_variant_clicked(self, box):
        if self.selected_variant_box:
            self.selected_variant_box.set_selected(False)
        box.set_selected(True)
        self.selected_variant_box = box
        
        if box.variant_code:
            detail_window = VariantDetailWindow(box.variant_code, self)
            detail_window.show()

    def update_variants_display(self):
        # Clear existing
        for box in self.variant_boxes:
            try: box.clicked.disconnect()
            except: pass
            box.deleteLater()
        self.variant_boxes.clear()
        
        variants = get_variants(self.char)
        
        if not variants:
            no_var = QLabel("No variants found.")
            no_var.setStyleSheet("color:#666; font-style:italic;")
            self.variants_layout.addWidget(no_var)
            return

        for variant_code, variant_char, img_path in variants:
            suffix = ""
            if variant_code and '-' in variant_code:
                suffix = f".{variant_code.split('-')[-1]}"
            
            box = VariantCharacterBox(
                char=(variant_char or "").strip(),
                code=suffix,
                img_path=(img_path or "").strip(),
                variant_code=variant_code
            )
            box.clicked.connect(self.on_variant_clicked)
            self.variants_layout.addWidget(box)
            self.variant_boxes.append(box)

# ═══════════════════════════════════════════════════════════════════════════
# 5. MAIN APPLICATION WINDOW
# ═══════════════════════════════════════════════════════════════════════════

class DictionaryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Chinese Character Dictionary')
        self.setGeometry(100, 100, 1100, 800)
        self.initUI()

    def initUI(self):
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #E8D4C8;")
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Search Bar ---
        search_frame = QFrame()
        search_frame.setStyleSheet("background:white; border-radius:10px; padding:10px;")
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(10, 5, 10, 5)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter character to search...")
        self.search_input.setStyleSheet(f"border:none; font-size:18px; font-family:{DEFAULT_FONTS};")
        self.search_input.returnPressed.connect(self.perform_search)
        
        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("background:#8B0000; color:white; padding:8px 20px; border-radius:5px; font-weight:bold;")
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.clicked.connect(self.perform_search)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        search_frame.setLayout(search_layout)
        layout.addWidget(search_frame)
        
        layout.addSpacing(15)
        
        # --- Tabs for Results ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #CCC; 
                top: -1px; 
            }
            QTabBar::tab { 
                background: #DDD; 
                padding: 8px 15px; /* Reduced horizontal padding */
                min-width: 120px;   /* Ensure a minimum width */
                border: 1px solid #CCC;
                border-bottom: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected { 
                background: white; 
                border-bottom: 2px solid white; 
                font-weight: bold;
            }
        """)
        
        # Tab 1: Text Results
        self.text_scroll = QScrollArea()
        self.text_scroll.setWidgetResizable(True)
        self.text_scroll.setStyleSheet("background:transparent; border:none;")
        self.text_container = QWidget()
        self.text_grid = QWidget() # Placeholder for grid
        self.text_scroll.setWidget(self.text_container)
        
        # Tab 2: Appendix Results
        self.appendix_scroll = QScrollArea()
        self.appendix_scroll.setWidgetResizable(True)
        self.appendix_scroll.setStyleSheet("background:transparent; border:none;")
        self.appendix_container = QWidget()
        self.appendix_scroll.setWidget(self.appendix_container)
        
        self.tabs.addTab(self.text_scroll, "Text Results")
        self.tabs.addTab(self.appendix_scroll, "Appendix")
        
        layout.addWidget(self.tabs)
        main_widget.setLayout(layout)

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
            
        search_char = query[0]
        text_results, appendix_results = get_search_results(search_char)
        
        # FIX: Loop through ALL rows and convert them to mutable lists
        text_results_mutable = []
        for row in text_results:
            row_list = list(row)
            # row_list[0] is the result_char (e.g., "丹A03410-003...")
            # We only want the very first character '丹'
            if row_list[0]:
                row_list[0] = row_list[0][0] 
            text_results_mutable.append(row_list)
        
        # Repeat for Appendix if necessary (though usually Appendix chars are already clean)
        appendix_mutable = [list(row) for row in appendix_results]
        
        self.populate_grid(self.text_scroll, text_results, is_text_type=True)
        self.populate_grid(self.appendix_scroll, appendix_results, is_text_type=False)
        
        # Update tab titles
        self.tabs.setTabText(0, f"Text Results ({len(text_results)})")
        self.tabs.setTabText(1, f"Appendix ({len(appendix_results)})")

    def populate_grid(self, scroll_area, results, is_text_type=True):
        # Create a new container widget for the grid
        container = QWidget()
        container.setStyleSheet("background: #FDFDFD;")
        grid = QGridLayout()
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(15)
        
        columns = 6
        row = 0
        col = 0
        
        if not results:
            lbl = QLabel("No results found.")
            lbl.setStyleSheet("color:#888; font-size:16px; padding:20px;")
            grid.addWidget(lbl, 0, 0)
        else:
            for item in results:
                if is_text_type:
                    # unpack: result_char, result_code, ucs_code, radical_stroke, detail_url, data_sn, icon_label
                    r_char, r_code, ucs, rs, url, sn, icon = item
                    full_text = f"{r_char}{r_code}" # simplified full text ID
                    bottom = r_code
                else:
                    # unpack: result_char, icon_label, ucs_code, radical_stroke, detail_url, appendix_id, anchor_id
                    r_char, icon, ucs, rs, url, app_id, anchor = item
                    full_text = f"Appendix:{app_id}"
                    bottom = icon or "Appendix"

                # Create Box
                box = SearchResultBox(
                    char=r_char,
                    alter_char=r_char[0][0],
                    bottom_label=bottom,
                    ucs_code=ucs,
                    icon_label=icon,
                    full_text=full_text
                )
                box.clicked.connect(self.on_result_clicked)
                
                grid.addWidget(box, row, col)
                
                col += 1
                if col >= columns:
                    col = 0
                    row += 1
        
        # Add a stretch to the last row and column to keep grid tight
        grid.setRowStretch(row + 1, 1)
        grid.setColumnStretch(columns, 1)
        
        container.setLayout(grid)
        scroll_area.setWidget(container)

    def on_result_clicked(self, full_text, ucs_code):
        # Determine main code from full text or db lookup
        # For simplicity in this example, we try to find the main code based on the clicked char
        # In a real scenario, you might parse 'full_text' or use 'ucs_code' to lookup the 'summary' table.
        
        # Try to extract a code pattern like A01234
        extracted_code = extract_code_from_text(full_text)
        
        char_info = None
        
        # 1. Try finding by extracted code
        if extracted_code:
            char_info = get_character_by_code(extracted_code)
        
        # 2. If not found, check if it's a variant code
        if not char_info and extracted_code:
            main_code = find_main_code_from_variant(extracted_code)
            if main_code:
                char_info = get_character_by_code(main_code)

        # 3. If still not found, try searching by the text itself (UCS code or Char)
        if not char_info:
            # Clean char from full_text
            clean_char = full_text[0] if full_text else ""
            char_info = get_character_info(clean_char)

        if char_info:
            code, char = char_info
            # Open Description Window
            self.desc_window = CharacterDescriptionWindow(char, code, self)
            self.desc_window.show()
        else:
            QMessageBox.information(self, "Info", f"Detailed description not found for {full_text}")

# ═══════════════════════════════════════════════════════════════════════════
# 6. ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import QGridLayout # Imported late for the grid logic

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Global stylesheet tweaks
    app.setStyleSheet("""
        QLineEdit { padding: 5px; border: 1px solid #CCC; border-radius: 4px; }
        QScrollBar:vertical { width: 10px; background: #F0F0F0; }
        QScrollBar::handle:vertical { background: #CCC; border-radius: 5px; }
        QScrollBar::handle:vertical:hover { background: #999; }
    """)
    
    window = DictionaryApp()
    window.show()
    sys.exit(app.exec_())