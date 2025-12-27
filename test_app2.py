import sys
import sqlite3
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QScrollArea, QMessageBox, QTextEdit, QDialog,
                             QTabWidget)
from PyQt5.QtGui import QFont, QPixmap, QCursor, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal

DB = "dictionary.db"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Font fallback for Chinese characters
CHINESE_FONTS = "'TW-Sung-Plus', 'SimSun', 'Microsoft YaHei', serif"
CHINESE_FONT_LIST = ['TW-Sung-Plus', 'SimSun', 'Microsoft YaHei']

def get_available_font():
    """Get first available font from the fallback list"""
    available = QFontDatabase().families()
    for font in CHINESE_FONT_LIST:
        if font in available:
            return font
    return 'SimSun'

def normalize_char(char):
    """Handle surrogate pairs for CJK Extension B/C/D/E/F characters"""
    if not char:
        return char
    try:
        char.encode('utf-8')
        return char
    except UnicodeEncodeError:
        try:
            return char.encode('utf-16', 'surrogatepass').decode('utf-16')
        except:
            return char

def apply_chinese_font(widget, size=14):
    """Apply Chinese font to a widget"""
    font = QFont(get_available_font(), size)
    widget.setFont(font)

def get_variants(char):
    """Get variant characters for a main character"""
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

def get_supplementary_chars(char):
    """Get supplementary characters (附收字) for a character"""
    char = normalize_char(char)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    # Query for supplementary characters linked to this main character
    cur.execute("""
        SELECT supplementary_code, supplementary_char, appendix_id, appendix_name, appendix_link
        FROM supplementary_chars 
        WHERE main_char=? 
        ORDER BY supplementary_code;
    """, (char,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_variant_details(variant_code):
    """Fetch variant details from variant_details table"""
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

def get_variant_summary_table(main_code):
    """Get summary table data for all variants (研訂瀏覽 tab)"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT variant_code, variant_char, radical_stroke, pronunciation_list
        FROM variant_summary 
        WHERE main_code=? 
        ORDER BY variant_code;
    """, (main_code,))
    rows = cur.fetchall()
    conn.close()
    return rows

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
    cur.execute("""
        SELECT standard_character, shuowen_etymology, character_style, 
               zhuyin_pronunciation, hanyu_pinyin, definition 
        FROM descriptions WHERE main_code=?;
    """, (row[0],))
    description = cur.fetchone()
    conn.close()
    return description

def get_supplementary_details(supplementary_code, appendix_id):
    """Get detailed information for a supplementary character from appendix table"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT char_form, radical_stroke, pronunciation, 
               word_examples, source_reference
        FROM appendix_details 
        WHERE supplementary_code=? AND appendix_id=?;
    """, (supplementary_code, appendix_id))
    row = cur.fetchone()
    conn.close()
    return row

def resolve_image_path(img_path):
    if not img_path:
        return None
    img_path = img_path.strip()
    if os.path.isabs(img_path) and os.path.exists(img_path):
        return img_path
    full_path = os.path.join(SCRIPT_DIR, img_path)
    if os.path.exists(full_path):
        return full_path
    if os.path.exists(img_path):
        return os.path.abspath(img_path)
    return None

def format_text_with_images(text, section_type="default"):
    if not text:
        return ""
    def replace_image(match):
        img_path = match.group(1).strip()
        resolved_path = resolve_image_path(img_path)
        if resolved_path:
            return f'<img src="file:///{resolved_path.replace(chr(92), "/")}" style="max-height: 28px; vertical-align: middle; margin: 0 2px;">'
        return f'[img:{img_path}]'
    text = re.sub(r'img:([^$$]*?\.png)\]', replace_image, text)
    if section_type == "shuowen":
        text = re.sub(r'(段注本[：:])', r'<br>\1', text)
        text = re.sub(r'(?<!^)(大徐本[：:])', r'<br>\1', text)
    elif section_type == "style":
        text = re.sub(r'。\s*「', r'。<br>「', text)
    elif section_type == "definition":
        text = re.sub(r'(?<!^)(\d+\.)\s*', r'<br><br>\1 ', text)
    text = text.replace('\n', '<br>')
    return f'<html><body style="font-family:{CHINESE_FONTS};font-size:14px;line-height:1.9;margin:0;padding:5px;">{text}</body></html>'


class SupplementaryDetailWindow(QDialog):
    """Window to display supplementary character details (附收字)"""
    def __init__(self, supplementary_code, appendix_id, appendix_name, parent=None):
        super().__init__(parent)
        self.supplementary_code = supplementary_code
        self.appendix_id = appendix_id
        self.appendix_name = appendix_name
        self.setFixedSize(90, 85)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet("""
            SupplementaryCharacterBox{
                background:#FFF8DC;
                border:1px solid #DAA520;
                border-radius:3px;
            }
            SupplementaryCharacterBox:hover{
                border:2px solid #8B0000;
                background:#FFEFD5;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        label_widget = QLabel(label)
        label_widget.setAlignment(Qt.AlignCenter)
        label_widget.setStyleSheet("color:#666;font-size:9px;background:transparent;border:none;")
        layout.addWidget(label_widget)
        
        char_widget = QLabel(char)
        char_widget.setAlignment(Qt.AlignCenter)
        char_widget.setStyleSheet(f"font-family:{CHINESE_FONTS};font-size:28px;color:#333;background:transparent;border:none;")
        apply_chinese_font(char_widget, 28)
        layout.addWidget(char_widget, 1)
        
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)


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
        label_layout = QVBoxLayout()
        label_layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size:13px;font-weight:bold;color:#333;background:transparent;border:none;")
        label.setWordWrap(True)
        label_layout.addWidget(label)
        self.label_frame.setLayout(label_layout)
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
        text_edit.setStyleSheet(f"QTextEdit{{font-family:{CHINESE_FONTS};font-size:14px;color:#333;background:white;border:none;}}")
        apply_chinese_font(text_edit, 14)
        text_edit.setMinimumHeight(min_height)
        self.content_layout.addWidget(text_edit)
    
    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def get_content_layout(self):
        return self.content_layout


class CharacterDictionary(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_char, self.current_code = "", ""
        self.variant_boxes, self.selected_variant_box = [], None
        self.supplementary_boxes = []
        self.chinese_font = get_available_font()
        self.detail_windows = []
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Chinese Character Dictionary (異體字字典)')
        self.setGeometry(100, 100, 1000, 900)
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #E8D4C8;")
        self.setCentralWidget(main_widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #E8D4C8;
            }
            QScrollBar:vertical {
                background-color: #F5F5F5;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #CCCCCC;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #AAAAAA;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #F5F5F5;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #CCCCCC;
                min-width: 20px;
                border-radius: 4px;
            }
        """)
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #E8D4C8;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background:transparent;")
        h_layout = QHBoxLayout()
        self.code_label = QLabel("")
        self.code_label.setStyleSheet("font-size:18px;font-weight:bold;color:#333;background:transparent;")
        h_layout.addWidget(self.code_label)
        self.main_char_label = QLabel("")
        self.main_char_label.setStyleSheet(f"font-size:48px;color:#8B0000;font-family:{CHINESE_FONTS};background:transparent;")
        apply_chinese_font(self.main_char_label, 48)
        h_layout.addWidget(self.main_char_label)
        self.stroke_label = QLabel("")
        self.stroke_label.setStyleSheet("font-size:14px;color:#666;background:transparent;")
        h_layout.addWidget(self.stroke_label)
        h_layout.addStretch()
        header.setLayout(h_layout)
        content_layout.addWidget(header)
        content_layout.addSpacing(20)
        
        # Input section
        input_frame = QFrame()
        input_frame.setStyleSheet("QFrame{background:white;border:1px solid #DDD;border-radius:5px;}")
        i_layout = QHBoxLayout()
        i_layout.setContentsMargins(15, 10, 15, 10)
        input_label = QLabel("輸入字符:")
        input_label.setStyleSheet("background:transparent;border:none;")
        i_layout.addWidget(input_label)
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("輸入一個字...")
        self.entry.setMaxLength(2)
        self.entry.setFixedWidth(150)
        apply_chinese_font(self.entry, 24)
        self.entry.setStyleSheet("QLineEdit{font-size:24px;padding:5px;border:2px solid #8B0000;border-radius:5px;background-color:white;}")
        self.entry.returnPressed.connect(self.search_character)
        i_layout.addWidget(self.entry)
        search_btn = QPushButton("查詢")
        search_btn.setStyleSheet("QPushButton{background:#8B0000;color:white;border:none;border-radius:5px;padding:8px 20px;font-weight:bold;}")
        search_btn.clicked.connect(self.search_character)
        i_layout.addWidget(search_btn)
        clear_btn = QPushButton("清除")
        clear_btn.setStyleSheet("QPushButton{background:#666;color:white;border:none;border-radius:5px;padding:8px 20px;}")
        clear_btn.clicked.connect(self.clear_all)
        i_layout.addWidget(clear_btn)
        i_layout.addStretch()
        input_frame.setLayout(i_layout)
        content_layout.addWidget(input_frame)
        content_layout.addSpacing(15)
        
        # Variants section (正文 - 異體字)
        content_layout.addWidget(SectionHeader("正文 - 異體字"))
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
        
        # Supplementary characters section (附收字)
        content_layout.addWidget(SectionHeader("附收字"))
        self.supplementary_container = QFrame()
        self.supplementary_container.setStyleSheet("QFrame{background:#FFFACD;border:1px solid #DDD;border-top:none;}")
        self.supplementary_scroll = QScrollArea()
        self.supplementary_scroll.setWidgetResizable(True)
        self.supplementary_scroll.setFixedHeight(100)
        self.supplementary_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.supplementary_widget = QWidget()
        self.supplementary_layout = QHBoxLayout()
        self.supplementary_layout.setContentsMargins(15, 10, 15, 10)
        self.supplementary_layout.setSpacing(8)
        self.supplementary_layout.setAlignment(Qt.AlignLeft)
        self.supplementary_widget.setLayout(self.supplementary_layout)
        self.supplementary_scroll.setWidget(self.supplementary_widget)
        s_layout = QVBoxLayout()
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.addWidget(self.supplementary_scroll)
        self.supplementary_container.setLayout(s_layout)
        content_layout.addWidget(self.supplementary_container)
        content_layout.addSpacing(15)
        
        # Description section (說明)
        content_layout.addWidget(SectionHeader("說明"))
        self.rows = [TableRow(l, i==5) for i, l in enumerate(["正字", "說文釋形", "字樣說明", "注音", "漢語拼音", "釋義"])]
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
            detail_window = VariantDetailWindow(box.variant_code, self.current_code, self)
            detail_window.show()
            self.detail_windows.append(detail_window)
    
    def on_supplementary_clicked(self, box):
        if box.supplementary_code and box.appendix_id:
            detail_window = SupplementaryDetailWindow(
                box.supplementary_code, 
                box.appendix_id, 
                box.appendix_name,
                self
            )
            detail_window.show()
            self.detail_windows.append(detail_window)
    
    def clear_variants_display(self):
        for box in self.variant_boxes:
            try:
                box.clicked.disconnect()
            except:
                pass
            box.deleteLater()
        self.variant_boxes.clear()
        self.selected_variant_box = None
        
        while self.variants_layout.count():
            item = self.variants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def clear_supplementary_display(self):
        for box in self.supplementary_boxes:
            try:
                box.clicked.disconnect()
            except:
                pass
            box.deleteLater()
        self.supplementary_boxes.clear()
        
        while self.supplementary_layout.count():
            item = self.supplementary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def update_variants_display(self, char):
        self.clear_variants_display()
        variants = get_variants(char)
        if not variants:
            no_variants_label = QLabel("此字無異體字")
            no_variants_label.setStyleSheet("""
                QLabel {
                    color: #999;
                    font-size: 14px;
                    font-style: italic;
                    padding: 10px 20px;
                    background: transparent;
                    border: none;
                }
            """)
            no_variants_label.setAlignment(Qt.AlignCenter)
            self.variants_layout.addStretch()
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
    
    def update_supplementary_display(self, char):
        self.clear_supplementary_display()
        supplementary_chars = get_supplementary_chars(char)
        if not supplementary_chars:
            no_supp_label = QLabel("此字無附收字")
            no_supp_label.setStyleSheet("""
                QLabel {
                    color: #999;
                    font-size: 14px;
                    font-style: italic;
                    padding: 10px 20px;
                    background: transparent;
                    border: none;
                }
            """)
            no_supp_label.setAlignment(Qt.AlignCenter)
            self.supplementary_layout.addStretch()
            self.supplementary_layout.addWidget(no_supp_label)
            self.supplementary_layout.addStretch()
            return
        
        for supp_code, supp_char, app_id, app_name, app_link in supplementary_chars:
            box = SupplementaryCharacterBox(
                (supp_char or "").strip(),
                app_name or "附錄",
                supp_code,
                app_id,
                app_name
            )
            box.clicked.connect(self.on_supplementary_clicked)
            self.supplementary_layout.addWidget(box)
            self.supplementary_boxes.append(box)
        self.supplementary_layout.addStretch()
    
    def get_first_character(self, text):
        """Extract first character, handling surrogate pairs"""
        if not text:
            return ""
        text = normalize_char(text)
        if len(text) >= 2:
            first_two = text[:2]
            try:
                first_two.encode('utf-8')
                if ord(text[0]) < 0xD800 or ord(text[0]) > 0xDFFF:
                    return text[0]
            except:
                pass
            return first_two
        return text
    
    def search_character(self):
        raw_text = self.entry.text().strip()
        if not raw_text:
            QMessageBox.warning(self, "輸入錯誤", "請輸入一個字符。")
            return
        
        char = self.get_first_character(raw_text)
        char = normalize_char(char)
        
        char_info = get_character_info(char)
        if not char_info:
            QMessageBox.information(self, "未找到", f"找不到「{char}」的信息。")
            return
        
        code, main_char = char_info
        self.current_char, self.current_code = main_char, code
        self.code_label.setText(code)
        self.main_char_label.setText(main_char)
        self.stroke_label.setText("--05-06")
        
        # Update variants and supplementary characters
        self.update_variants_display(char)
        self.update_supplementary_display(char)
        
        description = get_character_description(char)
        if not description:
            for row in self.rows:
                row.clear_content()
            return
        
        standard_char, shuowen, char_style, zhuyin, pinyin, definition = description
        data = [
            (f"[{code}] {main_char} --05-06", 18, None),
            (shuowen, None, "shuowen"),
            (char_style, None, "style"),
            (zhuyin, 24, None),
            (pinyin, 16, None),
            (definition, None, "definition")
        ]
        for i, (text, font_size, section) in enumerate(data):
            self.rows[i].clear_content()
            if section:
                self.rows[i].set_html_content(format_text_with_images(text or "", section), 80 if section != "definition" else 200)
            else:
                lbl = QLabel(text or "無資料")
                lbl.setStyleSheet(f"font-family:{CHINESE_FONTS};font-size:{font_size or 14}px;color:#333;background:transparent;border:none;")
                apply_chinese_font(lbl, font_size or 14)
                self.rows[i].get_content_layout().addWidget(lbl)
    
    def clear_all(self):
        self.entry.clear()
        self.code_label.setText("")
        self.main_char_label.setText("")
        self.stroke_label.setText("")
        for row in self.rows:
            row.clear_content()
        self.clear_variants_display()
        self.clear_supplementary_display()
        self.entry.setFocus()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = CharacterDictionary()
    window.show()
    sys.exit(app.exec_())


class SupplementaryDetailWindow(QDialog):
    """Window to display supplementary character details (附收字)"""
    def __init__(self, supplementary_code, appendix_id, appendix_name, parent=None):
        super().__init__(parent)
        self.supplementary_code = supplementary_code
        self.appendix_id = appendix_id
        self.appendix_name = appendix_name
        self.setWindowTitle(f'Supplementary Character - {supplementary_code}')
        self.setGeometry(150, 150, 800, 600)
        self.setStyleSheet("background-color: #E8D4C8;")
        self.initUI()
    
    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #E8D4C8;
            }
            QScrollBar:vertical {
                background-color: #F5F5F5;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #CCCCCC;
                min-height: 20px;
                border-radius: 4px;
            }
        """)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #E8D4C8;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        header = SectionHeader(f"附收字詳情 - {self.appendix_name}")
        content_layout.addWidget(header)
        
        details = get_supplementary_details(self.supplementary_code, self.appendix_id)
        
        if details:
            char_form, radical_stroke, pronunciation, word_examples, source_ref = details
            
            if char_form:
                row1 = TableRow("字形")
                self.add_text_label(row1, char_form, 24)
                content_layout.addWidget(row1)
            
            if radical_stroke:
                row2 = TableRow("部首筆畫")
                self.add_text_label(row2, radical_stroke, 14)
                content_layout.addWidget(row2)
            
            if pronunciation:
                row3 = TableRow("音讀")
                html = format_text_with_images(pronunciation, "default")
                row3.set_html_content(html, 60)
                content_layout.addWidget(row3)
            
            if word_examples:
                row4 = TableRow("詞語例或說明")
                html = format_text_with_images(word_examples, "default")
                row4.set_html_content(html, 100)
                content_layout.addWidget(row4)
            
            if source_ref:
                row5 = TableRow("來源參考", has_top_accent=True)
                self.add_text_label(row5, source_ref, 12)
                content_layout.addWidget(row5)
        else:
            no_data = QLabel("未找到附收字詳細信息")
            no_data.setStyleSheet("font-size:14px;color:#666;padding:20px;")
            no_data.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(no_data)
        
        content_layout.addStretch()
        
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background:transparent;border:none;")
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 15, 20, 15)
        btn_layout.addStretch()
        close_btn = QPushButton("關閉")
        close_btn.setStyleSheet("QPushButton{background:#666;color:white;border:none;border-radius:5px;padding:8px 25px;font-size:13px;}QPushButton:hover{background:#888;}")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        btn_frame.setLayout(btn_layout)
        content_layout.addWidget(btn_frame)
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
    
    def add_text_label(self, row, text, font_size=14):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-family:{CHINESE_FONTS};font-size:{font_size}px;color:#333;background:transparent;border:none;")
        apply_chinese_font(lbl, font_size)
        lbl.setWordWrap(True)
        row.get_content_layout().addWidget(lbl)


class VariantDetailWindow(QDialog):
    """Window to display variant character details with tabs"""
    def __init__(self, variant_code, main_code, parent=None):
        super().__init__(parent)
        self.variant_code = variant_code
        self.main_code = main_code
        self.setWindowTitle(f'異體字詳情 - {variant_code}')
        self.setGeometry(150, 150, 900, 750)
        self.setStyleSheet("background-color: #E8D4C8;")
        self.initUI()
    
    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CCC;
                background: #E8D4C8;
            }
            QTabBar::tab {
                background: #F5F5F0;
                border: 1px solid #CCC;
                padding: 8px 20px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #8B0000;
                color: white;
            }
        """)
        
        # Tab 1: 解說 (Explanation)
        explanation_tab = self.create_explanation_tab()
        tab_widget.addTab(explanation_tab, "解說")
        
        # Tab 2: 異體字 (Variants) - Show all variants
        variants_tab = self.create_variants_tab()
        tab_widget.addTab(variants_tab, "異體字")
        
        # Tab 3: 研訂瀏覽 (Summary View)
        summary_tab = self.create_summary_tab()
        tab_widget.addTab(summary_tab, "研訂瀏覽")
        
        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)
    
    def create_explanation_tab(self):
        """Create the explanation tab showing detailed variant info"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#E8D4C8;}")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #E8D4C8;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        header = SectionHeader("說明")
        content_layout.addWidget(header)
        
        details = get_variant_details(self.variant_code)
        
        if details:
            variant_code, standard_code, variant_char, key_refs, bopomofo, pinyin, researcher, explanation, glyph_path = details
            
            # Variant Character Row
            row1 = TableRow("異體字")
            row1_layout = row1.get_content_layout()
            char_widget = QWidget()
            char_h_layout = QHBoxLayout()
            char_h_layout.setContentsMargins(0, 0, 0, 0)
            char_h_layout.setSpacing(10)
            
            code_label = QLabel(f"[{variant_code}]")
            code_label.setStyleSheet(f"font-family:{CHINESE_FONTS};font-size:16px;color:#333;background:transparent;border:none;")
            apply_chinese_font(code_label, 16)
            char_h_layout.addWidget(code_label)
            
            resolved_glyph = resolve_image_path(glyph_path) if glyph_path else None
            if resolved_glyph:
                glyph_label = QLabel()
                pixmap = QPixmap(resolved_glyph)
                if not pixmap.isNull():
                    glyph_label.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                glyph_label.setStyleSheet("background:#E8E4D9;border:1px solid #CCC;padding:5px;")
                char_h_layout.addWidget(glyph_label)
            
            if variant_char:
                char_info_label = QLabel(variant_char)
                char_info_label.setStyleSheet(f"font-family:{CHINESE_FONTS};font-size:24px;color:#333;background:transparent;border:none;")
                apply_chinese_font(char_info_label, 24)
                char_h_layout.addWidget(char_info_label)
            
            char_h_layout.addStretch()
            char_widget.setLayout(char_h_layout)
            row1_layout.addWidget(char_widget)
            content_layout.addWidget(row1)
            
            # Content Row
            row2 = TableRow("內容")
            if key_refs:
                html = format_text_with_images(key_refs, "default")
                row2.set_html_content(html, 100)
            else:
                self.add_text_label(row2, "無資料")
            content_layout.addWidget(row2)
            
            # Research Notes Section
            has_research_data = any([bopomofo, pinyin, researcher, explanation])
            
            if has_research_data:
                research_header = SectionHeader("研訂說明")
                content_layout.addWidget(research_header)
                
                if bopomofo:
                    row3 = TableRow("注音")
                    self.add_text_label(row3, bopomofo, 24)
                    content_layout.addWidget(row3)
                
                if pinyin:
                    row4 = TableRow("漢語拼音")
                    self.add_text_label(row4, pinyin, 16)
                    content_layout.addWidget(row4)
                
                if researcher:
                    row5 = TableRow("研訂者")
                    self.add_text_label(row5, researcher, 14)
                    content_layout.addWidget(row5)
                
                if explanation:
                    row6 = TableRow("內容", has_top_accent=True)
                    html = format_text_with_images(explanation, "default")
                    row6.set_html_content(html, 150)
                    content_layout.addWidget(row6)
        else:
            no_data = QLabel("未找到異體字詳細信息")
            no_data.setStyleSheet("font-size:14px;color:#666;padding:20px;")
            no_data.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(no_data)
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        return scroll
    
    def create_variants_tab(self):
        """Create the variants tab showing all variant characters"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#E8D4C8;}")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #E8D4C8;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(10)
        
        header = SectionHeader("異體字列表")
        content_layout.addWidget(header)
        
        # Get all variants for the main character
        # Extract main code from variant code (e.g., A00124-001 -> A00124)
        main_code = self.variant_code.split('-')[0] if '-' in self.variant_code else self.main_code
        
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT variant_code, variant_char, img_path 
            FROM variants 
            WHERE main_code=? 
            ORDER BY variant_code;
        """, (main_code,))
        variants = cur.fetchall()
        conn.close()
        
        if variants:
            variants_container = QFrame()
            variants_container.setStyleSheet("background:white;border:1px solid #DDD;border-radius:5px;padding:15px;")
            variants_layout = QHBoxLayout()
            variants_layout.setSpacing(10)
            variants_layout.setAlignment(Qt.AlignLeft)
            
            for v_code, v_char, v_img in variants:
                v_box = VariantCharacterBox(v_char or "", f".{v_code.split('-')[-1]}", v_img or "", v_code)
                variants_layout.addWidget(v_box)
            
            variants_layout.addStretch()
            variants_container.setLayout(variants_layout)
            content_layout.addWidget(variants_container)
        else:
            no_variants = QLabel("無異體字")
            no_variants.setStyleSheet("font-size:14px;color:#666;padding:20px;")
            content_layout.addWidget(no_variants)
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        return scroll
    
    def create_summary_tab(self):
        """Create the summary tab showing all variants in table format (研訂瀏覽)"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#E8D4C8;}")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #E8D4C8;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        header = SectionHeader("研訂瀏覽")
        content_layout.addWidget(header)
        
        # Get summary data
        main_code = self.variant_code.split('-')[0] if '-' in self.variant_code else self.main_code
        summary_data = get_variant_summary_table(main_code)
        
        if summary_data:
            # Create table
            table_frame = QFrame()
            table_frame.setStyleSheet("background:white;border:1px solid #CCC;")
            table_layout = QVBoxLayout()
            table_layout.setContentsMargins(0, 0, 0, 0)
            table_layout.setSpacing(0)
            
            # Header row
            header_row = QFrame()
            header_row.setStyleSheet("background:#8B0000;border-bottom:2px solid #600000;")
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 0)
            
            headers = ["字形", "部首筆畫", "音讀"]
            widths = [100, 150, 400]
            for h_text, width in zip(headers, widths):
                h_label = QLabel(h_text)
                h_label.setFixedWidth(width)
                h_label.setStyleSheet("color:white;font-weight:bold;padding:10px;border-right:1px solid #600000;")
                h_label.setAlignment(Qt.AlignCenter)
                header_layout.addWidget(h_label)
            header_row.setLayout(header_layout)
            table_layout.addWidget(header_row)
            
            # Data rows
            for v_code, v_char, radical_stroke, pronunciation in summary_data:
                row_frame = QFrame()
                row_frame.setStyleSheet("background:white;border-bottom:1px solid #DDD;")
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(0, 0, 0, 0)
                
                # Character
                char_label = QLabel(v_char or "")
                char_label.setFixedWidth(100)
                char_label.setStyleSheet(f"font-family:{CHINESE_FONTS};font-size:20px;padding:8px;border-right:1px solid #DDD;")
                apply_chinese_font(char_label, 20)
                char_label.setAlignment(Qt.AlignCenter)
                row_layout.addWidget(char_label)
                
                # Radical-Stroke
                rs_label = QLabel(radical_stroke or "")
                rs_label.setFixedWidth(150)
                rs_label.setStyleSheet("padding:8px;border-right:1px solid #DDD;")
                rs_label.setAlignment(Qt.AlignCenter)
                row_layout.addWidget(rs_label)
                
                # Pronunciation
                pron_text = QTextEdit()
                pron_text.setReadOnly(True)
                pron_text.setHtml(format_text_with_images(pronunciation or "", "default"))
                pron_text.setFixedWidth(400)
                pron_text.setMaximumHeight(80)
                pron_text.setStyleSheet(f"font-family:{CHINESE_FONTS};padding:8px;border:none;")
                apply_chinese_font(pron_text, 12)
                row_layout.addWidget(pron_text)
                
                row_frame.setLayout(row_layout)
                table_layout.addWidget(row_frame)
            
            table_frame.setLayout(table_layout)
            content_layout.addWidget(table_frame)
        else:
            no_data = QLabel("無研訂資料")
            no_data.setStyleSheet("font-size:14px;color:#666;padding:20px;")
            content_layout.addWidget(no_data)
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        return scroll
    
    def add_text_label(self, row, text, font_size=14):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-family:{CHINESE_FONTS};font-size:{font_size}px;color:#333;background:transparent;border:none;")
        apply_chinese_font(lbl, font_size)
        lbl.setWordWrap(True)
        row.get_content_layout().addWidget(lbl)


class VariantCharacterBox(QFrame):
    clicked = pyqtSignal(object)
    
    def __init__(self, char="", code="", img_path="", variant_code="", parent=None):
        super().__init__(parent)
        self.char, self.code, self.is_selected = char, code, False
        self.variant_code = variant_code
        self.setFixedSize(70, 75)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self.code_label = QLabel(code)
        self.code_label.setAlignment(Qt.AlignCenter)
        self.code_label.setFixedHeight(15)
        layout.addWidget(self.code_label)
        resolved_img_path = resolve_image_path(img_path) if img_path else None
        self.char_label = QLabel()
        self.char_label.setAlignment(Qt.AlignCenter)
        if resolved_img_path:
            pixmap = QPixmap(resolved_img_path)
            if not pixmap.isNull():
                self.char_label.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.char_label.setText(char or "?")
                apply_chinese_font(self.char_label, 26)
            self.is_image = True
        else:
            self.char_label.setText(char or "")
            apply_chinese_font(self.char_label, 26)
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


class SupplementaryCharacterBox(QFrame):
    """Box for displaying supplementary characters (附收字)"""
    clicked = pyqtSignal(object)
    
    def __init__(self, char="", label="", supplementary_code="", appendix_id="", appendix_name="", parent=None):
        super().__init__(parent)
        self.char = char
        self.supplementary_code = supplementary_code
        self.appendix_id = appendix_id
        self.appendix_name = appendix_name
        self.set