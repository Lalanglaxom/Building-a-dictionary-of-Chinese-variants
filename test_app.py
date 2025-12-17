import sys
import sqlite3
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QScrollArea, QMessageBox, QTextEdit)
from PyQt5.QtGui import QFont, QPixmap, QCursor, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal

DB = "dictionary.db"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Font fallback for Chinese characters
CHINESE_FONTS = "'TW-Sung-Plus'"
CHINESE_FONT_LIST = ['TW-Sung-Plus']

def get_available_font():
    """Get first available font from the fallback list"""
    available = QFontDatabase().families()
    for font in CHINESE_FONT_LIST:
        if font in available:
            return font
    return 'SimSun'

def get_variants(char):
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

def get_character_info(char):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code, char FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    conn.close()
    return row

def get_character_description(char):
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


class VariantCharacterBox(QFrame):
    clicked = pyqtSignal(object)
    
    def __init__(self, char="", code="", img_path="", parent=None):
        super().__init__(parent)
        self.char, self.code, self.is_selected = char, code, False
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
                self.char_label.setFont(QFont(get_available_font(), 26))
            self.is_image = True
        else:
            self.char_label.setText(char or "")
            self.char_label.setFont(QFont(get_available_font(), 26))
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
        self.chinese_font = get_available_font()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Chinese Character Dictionary')
        self.setGeometry(100, 100, 1000, 900)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        h_layout = QHBoxLayout()
        self.code_label = QLabel("")
        self.code_label.setStyleSheet("font-size:18px;font-weight:bold;color:#333;")
        h_layout.addWidget(self.code_label)
        self.main_char_label = QLabel("")
        self.main_char_label.setStyleSheet(f"font-size:48px;color:#8B0000;font-family:{CHINESE_FONTS};")
        h_layout.addWidget(self.main_char_label)
        self.stroke_label = QLabel("")
        self.stroke_label.setStyleSheet("font-size:14px;color:#666;")
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
        i_layout.addWidget(QLabel("Enter Character:"))
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type one character...")
        self.entry.setMaxLength(1)
        self.entry.setFixedWidth(150)
        self.entry.setStyleSheet(f"QLineEdit{{font-family:{CHINESE_FONTS};font-size:24px;padding:5px;border:2px solid #8B0000;border-radius:5px;}}")
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
        
        # Variants section
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
        
        # Description section
        content_layout.addWidget(SectionHeader("Description"))
        self.rows = [TableRow(l, i==5) for i, l in enumerate(["Standard\nCharacter", "Shuowen\nEtymology", "Character\nStyle", "Zhuyin", "Hanyu\nPinyin", "Definition"])]
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
    
    def clear_variants_display(self):
        for box in self.variant_boxes:
            box.clicked.disconnect()
            box.deleteLater()
        self.variant_boxes.clear()
        self.selected_variant_box = None
    
    def update_variants_display(self, char):
        self.clear_variants_display()
        variants = get_variants(char)
        if not variants:
            self.variants_layout.addWidget(QLabel("No variants found"))
            return
        for variant_code, variant_char, img_path in variants:
            suffix = f".{variant_code.split('-')[-1]}" if variant_code and '-' in variant_code else ""
            box = VariantCharacterBox((variant_char or "").strip(), suffix, (img_path or "").strip())
            box.clicked.connect(self.on_variant_clicked)
            self.variants_layout.addWidget(box)
            self.variant_boxes.append(box)
        self.variants_layout.addStretch()
    
    def search_character(self):
        char = self.entry.text().strip()
        if not char:
            QMessageBox.warning(self, "Input Error", "Please enter a character.")
            return
        char_info = get_character_info(char)
        if not char_info:
            QMessageBox.information(self, "Not Found", f"No information found for '{char}'.")
            return
        code, main_char = char_info
        self.current_char, self.current_code = main_char, code
        self.code_label.setText(code)
        self.main_char_label.setText(main_char)
        self.stroke_label.setText("--05-06")
        self.update_variants_display(char)
        description = get_character_description(char)
        if not description:
            for row in self.rows:
                row.clear_content()
            return
        standard_char, shuowen, char_style, zhuyin, pinyin, definition = description
        data = [
            (f"[{code}] {main_char} --05-06", "18px", None),
            (shuowen, None, "shuowen"),
            (char_style, None, "style"),
            (zhuyin, "24px", None),
            (pinyin, "16px", None),
            (definition, None, "definition")
        ]
        for i, (text, font_size, section) in enumerate(data):
            self.rows[i].clear_content()
            if section:
                self.rows[i].set_html_content(format_text_with_images(text or "", section), 80 if section != "definition" else 200)
            else:
                lbl = QLabel(text or "No data")
                lbl.setStyleSheet(f"font-family:{CHINESE_FONTS};font-size:{font_size or '14px'};color:#333;background:transparent;border:none;")
                self.rows[i].get_content_layout().addWidget(lbl)
    
    def clear_all(self):
        self.entry.clear()
        self.code_label.setText("")
        self.main_char_label.setText("")
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