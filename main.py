import sys
import sqlite3
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QScrollArea, QMessageBox, QTextEdit)
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

DB = "dictionary.db"

def get_variants(char):
    """Fetch variants and image paths from database"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return []
    main_code = row[0]
    cur.execute("SELECT variant_char, img_path FROM variants WHERE main_code=?;", (main_code,))
    rows = cur.fetchall()
    conn.close()
    return rows

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

def format_text_with_images(text):
    """
    Converts text with image placeholders to HTML format for QTextEdit
    Format: [img:/path/to/image.png]
    Returns HTML string
    """
    if not text:
        return ""
    
    # Replace line breaks before numbered items with actual line breaks
    # This ensures each numbered item starts on a new line
    import re
    text = re.sub(r'(\d+\.)\s', r'\n\1 ', text)
    

    
    text = re.sub(r'$$img:([^$$]+)\]', replace_image, text)
    
    # Wrap in HTML
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial; font-size: 11px; line-height: 1.6; }}
            img {{ margin: 2px; border: 1px solid #8B4513; }}
        </style>
    </head>
    <body>
    {text}
    </body>
    </html>
    """
    return html

# Replace image placeholders with HTML img tags
def replace_image(match):
    img_path = match.group(1)
    if os.path.exists(img_path):
        # Convert path for HTML
        img_path_html = img_path.replace('\\', '/')
        return f'<br><img src="{img_path_html}" style="max-width: 45px; max-height: 45px; vertical-align: middle;"><br>'
    return "[img_not_found]"

class CharacterDictionary(QMainWindow):
    def __init__(self):
        super().__init__()
        self.media_player = QMediaPlayer()
        self.variant_pixmaps = []
        self.initUI()
        self.play_startup_music()
    
    def initUI(self):
        """Initialize the UI"""
        self.setWindowTitle('Chinese Character Dictionary')
        self.setGeometry(100, 100, 800, 1100)
        
        # Apply styling
        self.apply_style()
        
        # Create main widget with scroll area
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Input section
        input_section = self.create_input_section()
        main_layout.addWidget(input_section)
        
        # Section 1: Standard Character (正字)
        section1 = self.create_section1_standard_character()
        main_layout.addWidget(section1)
        
        # Section 2: Shuowen Etymology (說文釋形)
        section2 = self.create_section2_shuowen()
        main_layout.addWidget(section2)
        
        # Section 3: Character Style (字樣說明)
        section3 = self.create_section3_character_style()
        main_layout.addWidget(section3)
        
        # Section 4: Zhuyin (注音)
        section4 = self.create_section4_zhuyin()
        main_layout.addWidget(section4)
        
        # Section 5: Hanyu Pinyin (漢語拼音)
        section5 = self.create_section5_pinyin()
        main_layout.addWidget(section5)
        
        # Section 6: Definition (釋義)
        section6 = self.create_section6_definition()
        main_layout.addWidget(section6)
        
        # Footer
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
        main_layout.addStretch()
        
        # Set scroll content
        scroll_widget = QWidget()
        scroll_widget.setLayout(main_layout)
        scroll.setWidget(scroll_widget)
        
        # Set main layout
        main_central_layout = QVBoxLayout()
        main_central_layout.setContentsMargins(0, 0, 0, 0)
        main_central_layout.addWidget(scroll)
        main_widget.setLayout(main_central_layout)
    
    def apply_style(self):
        """Apply styling with background image"""
        image_path = r'resources\—Slidesdocs—simple chinese style border landscape_726a0d6c60.jpg'
        image_path_fixed = image_path.replace('\\', '/')
        
        style = f"""
            QMainWindow {{
                background-image: url('{image_path_fixed}');
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-color: #F5F5DC;
            }}
            
            QLabel {{
                color: #2F4F4F;
            }}
            
            QLabel#title {{
                color: #8B0000;
                font-size: 28px;
                font-weight: bold;
            }}
            
            QLabel#section-title {{
                color: #8B0000;
                font-size: 12px;
                font-weight: bold;
            }}
            
            QLineEdit {{
                background-color: #FFFACD;
                color: #2F4F4F;
                border: 2px solid #8B4513;
                border-radius: 5px;
                padding: 10px;
                font-size: 20px;
            }}
            
            QLineEdit:focus {{
                border: 2px solid #DC143C;
                background-color: #FFFEF0;
            }}
            
            QTextEdit {{
                background-color: #FFFACD;
                color: #2F4F4F;
                border: 1px solid #8B4513;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
            }}
            
            QTextEdit:read-only {{
                background-color: #FFFEF0;
            }}
            
            QPushButton {{
                background-color: #8B0000;
                color: #FFFACD;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: #DC143C;
            }}
            
            QPushButton:pressed {{
                background-color: #660000;
            }}
            
            QPushButton#secondary {{
                background-color: #4A708B;
            }}
            
            QPushButton#secondary:hover {{
                background-color: #5A8FA0;
            }}
            
            QFrame {{
                border: 2px solid #8B4513;
                border-radius: 5px;
                background-color: rgba(255, 250, 205, 0.9);
            }}
            
            QFrame#header {{
                border: none;
                background-color: transparent;
            }}
            
            QScrollArea {{
                border: 1px solid #8B4513;
                background-color: #FFFACD;
            }}
        """
        self.setStyleSheet(style)
    
    def create_header(self):
        """Create simple header"""
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 15, 0, 15)
        header_layout.setSpacing(5)
        
        title = QLabel('Chinese Character Dictionary')
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        return header_widget
    
    def create_input_section(self):
        """Create input section"""
        input_frame = QFrame()
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setSpacing(10)
        
        label = QLabel('Enter a Chinese character:')
        label.setFont(QFont('Arial', 12))
        input_layout.addWidget(label)
        
        self.entry = QLineEdit()
        self.entry.setPlaceholderText('Type one character...')
        self.entry.setAlignment(Qt.AlignCenter)
        self.entry.setMaxLength(1)
        self.entry.returnPressed.connect(self.search_variants)
        self.entry.setFocus()
        input_layout.addWidget(self.entry)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        search_btn = QPushButton('Search')
        search_btn.clicked.connect(self.search_variants)
        button_layout.addWidget(search_btn)
        
        clear_btn = QPushButton('Clear')
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.clear_input)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        input_layout.addLayout(button_layout)
        
        input_frame.setLayout(input_layout)
        return input_frame
    
    def create_section1_standard_character(self):
        """Section 1: Standard Character (正字)"""
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        title = QLabel('Standard Character (正字):')
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        self.section1_text = QTextEdit()
        self.section1_text.setReadOnly(True)
        self.section1_text.setMaximumHeight(60)
        layout.addWidget(self.section1_text)
        
        frame.setLayout(layout)
        return frame
    
    def create_section2_shuowen(self):
        """Section 2: Shuowen Etymology (說文釋形)"""
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        title = QLabel('Shuowen Etymology (說文釋形):')
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        self.section2_text = QTextEdit()
        self.section2_text.setReadOnly(True)
        self.section2_text.setMaximumHeight(100)
        layout.addWidget(self.section2_text)
        
        frame.setLayout(layout)
        return frame
    
    def create_section3_character_style(self):
        """Section 3: Character Style (字樣說明)"""
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        title = QLabel('Character Style (字樣說明):')
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        self.section3_text = QTextEdit()
        self.section3_text.setReadOnly(True)
        self.section3_text.setMaximumHeight(100)
        layout.addWidget(self.section3_text)
        
        frame.setLayout(layout)
        return frame
    
    def create_section4_zhuyin(self):
        """Section 4: Zhuyin Pronunciation (注音)"""
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        title = QLabel('Zhuyin Pronunciation (注音):')
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        self.section4_text = QTextEdit()
        self.section4_text.setReadOnly(True)
        self.section4_text.setMaximumHeight(40)
        layout.addWidget(self.section4_text)
        
        frame.setLayout(layout)
        return frame
    
    def create_section5_pinyin(self):
        """Section 5: Hanyu Pinyin (漢語拼音)"""
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        title = QLabel('Hanyu Pinyin (漢語拼音):')
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        self.section5_text = QTextEdit()
        self.section5_text.setReadOnly(True)
        self.section5_text.setMaximumHeight(40)
        layout.addWidget(self.section5_text)
        
        frame.setLayout(layout)
        return frame
    
    def create_section6_definition(self):
        """Section 6: Definition (釋義) - with HTML support for images"""
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        title = QLabel('Definition (釋義):')
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        self.section6_text = QTextEdit()
        self.section6_text.setReadOnly(True)
        self.section6_text.setMaximumHeight(200)
        layout.addWidget(self.section6_text)
        
        frame.setLayout(layout)
        return frame
    
    def create_footer(self):
        """Create footer with controls"""
        footer_frame = QFrame()
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 10, 15, 10)
        
        footer_layout.addStretch()
        
        self.music_btn = QPushButton('🔊 Music')
        self.music_btn.setObjectName("secondary")
        self.music_btn.setMaximumWidth(80)
        self.music_btn.clicked.connect(self.toggle_music)
        footer_layout.addWidget(self.music_btn)
        
        exit_btn = QPushButton('Exit')
        exit_btn.setObjectName("secondary")
        exit_btn.setMaximumWidth(60)
        exit_btn.clicked.connect(self.close)
        footer_layout.addWidget(exit_btn)
        
        footer_frame.setLayout(footer_layout)
        return footer_frame
    
    def search_variants(self):
        """Search for character and display all six sections"""
        char = self.entry.text().strip()
        
        if not char:
            QMessageBox.warning(self, "Input Error", "Please enter a character.")
            return
        
        # Clear all sections
        self.section1_text.setText('')
        self.section2_text.setText('')
        self.section3_text.setText('')
        self.section4_text.setText('')
        self.section5_text.setText('')
        self.section6_text.setText('')
        
        # Get description
        description = get_character_description(char)
        if not description:
            QMessageBox.information(self, "Not Found", f"No information found for '{char}'.")
            self.section1_text.setText("No data available")
            return
        
        standard_char, shuowen, char_style, zhuyin, pinyin, definition = description
        
        # Populate all six sections with image support
        self.section1_text.setMarkdown(standard_char if standard_char else "No data available")
        
        # Section 2: Shuowen - with images
        if shuowen:
            self.section2_text.setHtml(format_text_with_images(shuowen))
        else:
            self.section2_text.setText("No data available")
        
        # Section 3: Character Style - with images
        if char_style:
            self.section3_text.setHtml(format_text_with_images(char_style))
        else:
            self.section3_text.setText("No data available")
        
        self.section4_text.setText(zhuyin if zhuyin else "No data available")
        self.section5_text.setText(pinyin if pinyin else "No data available")
        
        # Section 6: Definition - with images and numbered line breaks
        if definition:
            self.section6_text.setHtml(format_text_with_images(definition))
        else:
            self.section6_text.setText("No data available")
    
    def clear_input(self):
        """Clear all inputs and results"""
        self.entry.clear()
        self.section1_text.setText('')
        self.section2_text.setText('')
        self.section3_text.setText('')
        self.section4_text.setText('')
        self.section5_text.setText('')
        self.section6_text.setText('')
        self.entry.setFocus()
    
    def play_startup_music(self):
        """Play startup music on app launch"""
        music_file = r'E:\Benkyute Kudasai\Chinese\Building-a-dictionary-of-Chinese-variants\resources\China famous funny sound effect.mp3'
        
        if os.path.exists(music_file):
            try:
                media_content = QMediaContent(QUrl.fromLocalFile(music_file))
                self.media_player.setMedia(media_content)
            except Exception as e:
                print(f"Could not load music: {e}")
    
    def toggle_music(self):
        """Toggle music on/off"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.music_btn.setText('🔇 Music')
        else:
            self.media_player.play()
            self.music_btn.setText('🔊 Music')


def main():
    app = QApplication(sys.argv)
    window = CharacterDictionary()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()