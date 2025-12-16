import sys
import sqlite3
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QScrollArea, QMessageBox, QTextEdit,
                             QGridLayout, QSizePolicy)
from PyQt5.QtGui import QFont, QPixmap, QColor, QPainter, QCursor
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

DB = "dictionary.db"

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_variants(char):
    """Fetch variants with their codes and image paths from database"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return []
    main_code = row[0]
    cur.execute("""
        SELECT variant_code, variant_char, img_path 
        FROM variants 
        WHERE main_code=?
        ORDER BY variant_code;
    """, (main_code,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_character_info(char):
    """Fetch character code and info from summary table"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code, char FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    conn.close()
    return row

def get_character_description(char):
    """Fetch character description from descriptions table"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    
    main_code = row[0]
    cur.execute("""
        SELECT standard_character, shuowen_etymology, character_style, 
               zhuyin_pronunciation, hanyu_pinyin, definition 
        FROM descriptions WHERE main_code=?;
    """, (main_code,))
    
    description = cur.fetchone()
    conn.close()
    return description

def resolve_image_path(img_path):
    """Resolve image path - handles both relative and absolute paths"""

    if not img_path:
        return None
    
    img_path = img_path.strip()
    
    # If it's already absolute and exists, return it
    if os.path.isabs(img_path) and os.path.exists(img_path):
        return img_path
    
    # Try relative to script directory
    full_path = os.path.join(SCRIPT_DIR, img_path)
    if os.path.exists(full_path):
        return full_path
    
    # Try relative to current working directory
    if os.path.exists(img_path):
        return os.path.abspath(img_path)
    
    return None

def format_text_with_images(text, section_type="default"):
    """
    Converts text with image placeholders to HTML format for QTextEdit
    Format: [img:path/to/image.png]
    section_type: "shuowen", "style", "definition", or "default"
    Returns HTML string
    """
    if not text:
        return ""
    
    # Replace image placeholders with HTML img tags
    def replace_image(match):
        img_path = match.group(1).strip()
        print(img_path)
        resolved_path = resolve_image_path(img_path)
        
        
        if resolved_path:
            # Normalize path separators and use file:/// protocol
            img_path_html = resolved_path.replace('\\', '/')
            return f'<img src="file:///{img_path_html}" style="max-height: 28px; vertical-align: middle; margin: 0 2px;">'
        return f'[img:{img_path}]'
    
    # Replace [img:path] with actual images
    text = re.sub(r'img:([^$$]*?\.png)\]', replace_image, text)
    
    
    # Handle line breaks based on section type
    if section_type == "shuowen":
        # Add line break before "段注本" 
        text = re.sub(r'(段注本[：:])', r'<br>\1', text)
        # Add line break before "大徐本" if not at start
        text = re.sub(r'(?<!^)(大徐本[：:])', r'<br>\1', text)
        
    elif section_type == "style":
        # Add line breaks before specific patterns
        # Break before 「 when it follows 。
        text = re.sub(r'。\s*「', r'。<br>「', text)
        # Break before sentences starting with specific patterns
        text = re.sub(r'。\s*([「『]?[^\s]{1,4}[」』]?等字)', r'。<br>\1', text)
        
    elif section_type == "definition":
        # Add line break before each numbered item (except the first)
        text = re.sub(r'(?<!^)(\d+\.)\s*', r'<br><br>\1 ', text)
    
    # Replace explicit newlines with <br>
    text = text.replace('\n', '<br>')
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ 
                font-family: 'Microsoft YaHei', 'SimSun', Arial; 
                font-size: 14px; 
                line-height: 1.9; 
                margin: 0; 
                padding: 5px;
                color: #333;
            }}
            img {{ 
                margin: 0 3px; 
                vertical-align: middle;
            }}
        </style>
    </head>
    <body>
    {text}
    </body>
    </html>
    """
    return html


class VariantCharacterBox(QFrame):
    """Individual variant character display box - clickable, supports text or image"""
    clicked = pyqtSignal(object)
    
    def __init__(self, char="", code="", img_path="", parent=None):
        super().__init__(parent)
        self.char = char
        self.code = code
        self.img_path = img_path
        self.is_selected = False
        
        self.setFixedSize(70, 75)
        self.setContentsMargins(0, 0, 0, 0)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        
        # Code label (small, at top)
        self.code_label = QLabel(code if code else "")
        self.code_label.setAlignment(Qt.AlignCenter)
        self.code_label.setFixedHeight(15)
        layout.addWidget(self.code_label)
        
        # Check if we should display image or text
        resolved_img_path = resolve_image_path(img_path) if img_path else None
        
        if resolved_img_path:
            # Display image
            self.char_label = QLabel()
            self.char_label.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(resolved_img_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.char_label.setPixmap(scaled_pixmap)
            else:
                self.char_label.setText(char if char else "?")
                self.char_label.setFont(QFont('SimSun', 26))
            self.is_image = True
        else:
            # Display text character
            self.char_label = QLabel(char if char else "")
            self.char_label.setAlignment(Qt.AlignCenter)
            self.char_label.setFont(QFont('SimSun', 26))
            self.is_image = False
        
        layout.addWidget(self.char_label, 1)
        
        self.setLayout(layout)
        self.update_style()
    
    def update_style(self):
        """Update the visual style based on selection state"""
        if self.is_selected:
            self.setStyleSheet("""
                VariantCharacterBox {
                    background-color: #8B0000;
                    border: 1px solid #600000;
                }
            """)
            self.code_label.setStyleSheet("color: white; background: transparent; border: none; font-size: 9px;")
            if not self.is_image:
                self.char_label.setStyleSheet("color: white; background: transparent; border: none;")
            else:
                self.char_label.setStyleSheet("background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                VariantCharacterBox {
                    background-color: white;
                    border: 1px solid #999;
                }
                VariantCharacterBox:hover {
                    border: 2px solid #8B0000;
                    background-color: #FFF8F8;
                }
            """)
            self.code_label.setStyleSheet("color: #666; background: transparent; border: none; font-size: 9px;")
            if not self.is_image:
                self.char_label.setStyleSheet("color: #333; background: transparent; border: none;")
            else:
                self.char_label.setStyleSheet("background: transparent; border: none;")
    
    def set_selected(self, selected):
        """Set the selection state"""
        self.is_selected = selected
        self.update_style()
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)


class SectionHeader(QFrame):
    """Red section header bar"""
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setFixedHeight(35)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 0, 15, 0)
        
        # White accent bar on left
        accent = QFrame()
        accent.setFixedSize(4, 20)
        accent.setStyleSheet("background-color: white; border: none;")
        layout.addWidget(accent)
        
        label = QLabel(text)
        label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(label)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet("QFrame { background-color: #8B0000; border: none; }")


class TableRow(QFrame):
    """Table row with label and content"""
    def __init__(self, label_text, has_top_accent=False, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        self.has_top_accent = has_top_accent
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add red accent line at top if needed
        if has_top_accent:
            accent_line = QFrame()
            accent_line.setFixedHeight(3)
            accent_line.setStyleSheet("background-color: #8B0000; border: none;")
            main_layout.addWidget(accent_line)
        
        # Row content
        row_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Label cell
        self.label_frame = QFrame()
        self.label_frame.setFixedWidth(100)
        self.label_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F0;
                border: 1px solid #CCC;
                border-right: none;
            }
        """)
        
        label_layout = QVBoxLayout()
        label_layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 13px; font-weight: bold; color: #333; background: transparent; border: none;")
        label.setWordWrap(True)
        label_layout.addWidget(label)
        self.label_frame.setLayout(label_layout)
        
        layout.addWidget(self.label_frame)
        
        # Content cell
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #CCC;
            }
        """)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(10, 8, 10, 8)
        self.content_frame.setLayout(self.content_layout)
        
        layout.addWidget(self.content_frame, 1)
        
        row_widget.setLayout(layout)
        main_layout.addWidget(row_widget)
        
        self.setLayout(main_layout)
    
    def set_text_content(self, text):
        """Set plain text content"""
        self.clear_content()
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; color: #333; background: transparent; border: none;")
        self.content_layout.addWidget(label)
    
    def set_html_content(self, html, min_height=60):
        """Set HTML content with QTextEdit"""
        self.clear_content()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(html)
        text_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                color: #333;
                background: white;
                border: none;
            }
        """)
        text_edit.setMinimumHeight(min_height)
        text_edit.document().setTextWidth(text_edit.viewport().width())
        doc_height = text_edit.document().size().height()
        text_edit.setMinimumHeight(max(min_height, int(doc_height) + 20))
        
        self.content_layout.addWidget(text_edit)
        return text_edit
    
    def clear_content(self):
        """Clear all content from the content layout"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def get_content_layout(self):
        return self.content_layout


class CharacterDictionary(QMainWindow):
    def __init__(self):
        super().__init__()
        self.media_player = QMediaPlayer()
        self.current_char = ""
        self.current_code = ""
        self.variant_boxes = []
        self.selected_variant_box = None
        self.initUI()
    
    def initUI(self):
        """Initialize the UI"""
        self.setWindowTitle('Chinese Character Dictionary')
        self.setGeometry(100, 100, 1000, 900)
        self.setStyleSheet("background-color: #F5F5F0;")
        
        # Create main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #F5F5F0; }")
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)
        
        # Header with character info
        self.header = self.create_header()
        content_layout.addWidget(self.header)
        content_layout.addSpacing(20)
        
        # Tab buttons
        tabs = self.create_tabs()
        content_layout.addWidget(tabs)
        content_layout.addSpacing(15)
        
        # Input section (for searching)
        input_section = self.create_input_section()
        content_layout.addWidget(input_section)
        content_layout.addSpacing(15)
        
        # Variants section
        self.variants_header = SectionHeader("Variants")
        content_layout.addWidget(self.variants_header)
        
        self.variants_container = QFrame()
        self.variants_container.setStyleSheet("""
            QFrame {
                background-color: #F8F8F5;
                border: 1px solid #DDD;
                border-top: none;
            }
        """)
        self.variants_scroll = QScrollArea()
        self.variants_scroll.setWidgetResizable(True)
        self.variants_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.variants_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.variants_scroll.setFixedHeight(100)
        self.variants_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.variants_widget = QWidget()
        self.variants_layout = QHBoxLayout()
        self.variants_layout.setContentsMargins(15, 10, 15, 10)
        self.variants_layout.setSpacing(8)
        self.variants_layout.setAlignment(Qt.AlignLeft)
        self.variants_widget.setLayout(self.variants_layout)
        self.variants_scroll.setWidget(self.variants_widget)
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.variants_scroll)
        self.variants_container.setLayout(container_layout)
        
        content_layout.addWidget(self.variants_container)
        content_layout.addSpacing(15)
        
        # Description section
        desc_header = SectionHeader("Description")
        content_layout.addWidget(desc_header)
        
        # Table rows
        self.table_container = QFrame()
        self.table_container.setStyleSheet("background: transparent; border: none;")
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)
        
        # Row 1: Standard Character
        self.row1 = TableRow("Standard\nCharacter")
        table_layout.addWidget(self.row1)
        
        # Row 2: Shuowen Etymology
        self.row2 = TableRow("Shuowen\nEtymology")
        table_layout.addWidget(self.row2)
        
        # Row 3: Character Style
        self.row3 = TableRow("Character\nStyle")
        table_layout.addWidget(self.row3)
        
        # Row 4: Zhuyin
        self.row4 = TableRow("Zhuyin")
        table_layout.addWidget(self.row4)
        
        # Row 5: Hanyu Pinyin
        self.row5 = TableRow("Hanyu\nPinyin")
        table_layout.addWidget(self.row5)
        
        # Row 6: Definition - with red accent line at top
        self.row6 = TableRow("Definition", has_top_accent=True)
        table_layout.addWidget(self.row6)
        
        self.table_container.setLayout(table_layout)
        content_layout.addWidget(self.table_container)
        
        content_layout.addStretch()
        
        # Footer
        footer = self.create_footer()
        content_layout.addWidget(footer)
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        
        # Set main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        main_widget.setLayout(main_layout)
    
    def create_header(self):
        """Create header with character code and info"""
        header = QFrame()
        header.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Code label
        self.code_label = QLabel("")
        self.code_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(self.code_label)
        
        # Main character (large, red)
        self.main_char_label = QLabel("")
        self.main_char_label.setStyleSheet("font-size: 48px; color: #8B0000; font-family: 'SimSun', serif;")
        layout.addWidget(self.main_char_label)
        
        # Stroke info
        self.stroke_label = QLabel("")
        self.stroke_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(self.stroke_label)
        
        layout.addStretch()
        header.setLayout(layout)
        return header
    
    def create_tabs(self):
        """Create tab buttons"""
        tabs = QFrame()
        tabs.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab 1: Explanation (active style)
        tab1 = QPushButton("Explanation")
        tab1.setFixedSize(100, 35)
        tab1.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: white;
                border: 1px solid #8B0000;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        layout.addWidget(tab1)
        
        # Tab 2: Variants
        tab2 = QPushButton("Variants")
        tab2.setFixedSize(100, 35)
        tab2.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F0;
                color: #8B0000;
                border: 1px solid #CCC;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #EEE;
            }
        """)
        layout.addWidget(tab2)
        
        # Tab 3: Review
        tab3 = QPushButton("Review")
        tab3.setFixedSize(100, 35)
        tab3.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F0;
                color: #8B0000;
                border: 1px solid #CCC;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #EEE;
            }
        """)
        layout.addWidget(tab3)
        
        layout.addStretch()
        tabs.setLayout(layout)
        return tabs
    
    def create_input_section(self):
        """Create input section for searching"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #DDD;
                border-radius: 5px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        
        label = QLabel("Enter Character:")
        label.setStyleSheet("font-size: 14px; color: #333; border: none; background: transparent;")
        layout.addWidget(label)
        
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type one character...")
        self.entry.setMaxLength(1)
        self.entry.setFixedWidth(150)
        self.entry.setStyleSheet("""
            QLineEdit {
                font-size: 24px;
                padding: 5px 10px;
                border: 2px solid #8B0000;
                border-radius: 5px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #DC143C;
            }
        """)
        self.entry.returnPressed.connect(self.search_character)
        layout.addWidget(self.entry)
        
        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #A00000;
            }
        """)
        search_btn.clicked.connect(self.search_character)
        layout.addWidget(search_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #888;
            }
        """)
        clear_btn.clicked.connect(self.clear_all)
        layout.addWidget(clear_btn)
        
        layout.addStretch()
        frame.setLayout(layout)
        return frame
    
    def create_footer(self):
        """Create footer with controls"""
        footer = QFrame()
        footer.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 20, 0, 10)
        
        layout.addStretch()
        
        self.music_btn = QPushButton("🔊 Music")
        self.music_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A708B;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5A8FA0;
            }
        """)
        self.music_btn.clicked.connect(self.toggle_music)
        layout.addWidget(self.music_btn)
        
        exit_btn = QPushButton("Exit")
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #888;
            }
        """)
        exit_btn.clicked.connect(self.close)
        layout.addWidget(exit_btn)
        
        footer.setLayout(layout)
        return footer
    
    def on_variant_clicked(self, box):
        """Handle variant box click"""
        if self.selected_variant_box is not None:
            self.selected_variant_box.set_selected(False)
        
        box.set_selected(True)
        self.selected_variant_box = box
    
    def clear_variants_display(self):
        """Clear all variant boxes"""
        for box in self.variant_boxes:
            box.clicked.disconnect()
            box.setParent(None)
            box.deleteLater()
        self.variant_boxes.clear()
        self.selected_variant_box = None
        
        while self.variants_layout.count():
            item = self.variants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def extract_variant_code_suffix(self, variant_code):
        """Extract the suffix part from variant_code (e.g., 'A00016-002' -> '.002')"""
        if not variant_code:
            return ""
        if '-' in variant_code:
            suffix = variant_code.split('-')[-1]
            return f".{suffix}"
        return ""
    
    def update_variants_display(self, char):
        """Update the variants display section"""
        self.clear_variants_display()
        
        variants = get_variants(char)
        
        if not variants:
            no_variants_label = QLabel("No variants found")
            no_variants_label.setStyleSheet("color: #666; font-size: 14px;")
            self.variants_layout.addWidget(no_variants_label)
            return
        
        for variant_code, variant_char, img_path in variants:
            display_code = self.extract_variant_code_suffix(variant_code)
            clean_char = variant_char.strip() if variant_char else ""
            clean_img_path = img_path.strip() if img_path else ""
            
            box = VariantCharacterBox(clean_char, display_code, clean_img_path)
            box.clicked.connect(self.on_variant_clicked)
            self.variants_layout.addWidget(box)
            self.variant_boxes.append(box)
        
        self.variants_layout.addStretch()
    
    def search_character(self):
        """Search for character and display information"""
        char = self.entry.text().strip()
        
        if not char:
            QMessageBox.warning(self, "Input Error", "Please enter a character.")
            return
        
        char_info = get_character_info(char)
        if not char_info:
            QMessageBox.information(self, "Not Found", f"No information found for '{char}'.")
            return
        
        code, main_char = char_info
        self.current_char = main_char
        self.current_code = code
        
        # Update header
        self.code_label.setText(f"{code}")
        self.main_char_label.setText(main_char)
        self.stroke_label.setText("--05-06")
        
        # Update variants
        self.update_variants_display(char)
        
        # Get description
        description = get_character_description(char)
        if not description:
            self.clear_description()
            return
        
        standard_char, shuowen, char_style, zhuyin, pinyin, definition = description
        
        # Row 1: Standard Character
        self.row1.clear_content()
        std_label = QLabel(f"[{code}] {main_char} --05-06" if standard_char else "No data")
        std_label.setStyleSheet("font-size: 18px; color: #333; background: transparent; border: none; font-family: 'SimSun', serif;")
        self.row1.get_content_layout().addWidget(std_label)
        
        # Row 2: Shuowen Etymology - with inline images and line breaks
        self.row2.clear_content()
        if shuowen:
            html = format_text_with_images(shuowen, section_type="shuowen")
            self.row2.set_html_content(html, min_height=100)
        else:
            self.row2.set_text_content("No data available")
        
        # Row 3: Character Style - with inline images and line breaks
        self.row3.clear_content()
        if char_style:
            html = format_text_with_images(char_style, section_type="style")
            self.row3.set_html_content(html, min_height=80)
        else:
            self.row3.set_text_content("No data available")
        
        # Row 4: Zhuyin
        self.row4.clear_content()
        zhuyin_label = QLabel(zhuyin if zhuyin else "No data")
        zhuyin_label.setStyleSheet("font-size: 24px; color: #333; background: transparent; border: none;")
        self.row4.get_content_layout().addWidget(zhuyin_label)
        
        # Row 5: Hanyu Pinyin
        self.row5.clear_content()
        pinyin_label = QLabel(pinyin if pinyin else "No data")
        pinyin_label.setStyleSheet("font-size: 16px; color: #333; background: transparent; border: none;")
        self.row5.get_content_layout().addWidget(pinyin_label)
        
        # Row 6: Definition - with line breaks for numbered items
        self.row6.clear_content()
        if definition:
            html = format_text_with_images(definition, section_type="definition")
            self.row6.set_html_content(html, min_height=200)
        else:
            self.row6.set_text_content("No data available")
    
    def clear_description(self):
        """Clear all description fields"""
        self.row1.clear_content()
        self.row2.clear_content()
        self.row3.clear_content()
        self.row4.clear_content()
        self.row5.clear_content()
        self.row6.clear_content()
    
    def clear_all(self):
        """Clear all inputs and results"""
        self.entry.clear()
        self.code_label.setText("")
        self.main_char_label.setText("")
        self.stroke_label.setText("")
        self.clear_description()
        self.clear_variants_display()
        self.entry.setFocus()
    
    def toggle_music(self):
        """Toggle music on/off"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.music_btn.setText('🔇 Music')
        else:
            music_file = r'resources\music.mp3'
            if os.path.exists(music_file):
                media_content = QMediaContent(QUrl.fromLocalFile(music_file))
                self.media_player.setMedia(media_content)
                self.media_player.play()
                self.music_btn.setText('🔊 Music')


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = CharacterDictionary()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()