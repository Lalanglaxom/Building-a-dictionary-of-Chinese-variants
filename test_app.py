import sys
import sqlite3
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QScrollArea, QMessageBox)
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
        self.setGeometry(100, 100, 539, 700)
        
        # Set background image
        # self.set_background_image(r'E:\Benkyute Kudasai\Chinese\Building-a-dictionary-of-Chinese-variants\resources\background.jpg')
        
        # Apply styling
        self.apply_style()
        
        # Create main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
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
        
        # Result section
        result_section = self.create_result_section()
        main_layout.addWidget(result_section)
        
        # Footer
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
        main_layout.addStretch()
        main_widget.setLayout(main_layout)
    
    def set_background_image(self, image_path):
        """Set background image"""
        if os.path.exists(image_path):
            # Convert backslashes to forward slashes for stylesheet
            image_path_fixed = image_path.replace('\\', '/')
            stylesheet = f"""
                QMainWindow {{
                    background-image: url('{image_path_fixed}');
                    background-position: center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    background-color: #F5F5DC;
                }}
            """
            self.setStyleSheet(stylesheet)
        # else:
        #     print(f"Background image not found at: {image_path}")
        #     stylesheet = """
        #         QMainWindow {
        #             background-color: #F5F5DC;
        #         }
        #     """
            self.setStyleSheet(stylesheet)
        
    def apply_style(self):
        
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
            
            QLabel#subtitle {{
                color: #A0522D;
                font-size: 12px;
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
            
            QFrame#title {{
                border: none;
                background-color: transparent;
            }}
            
            QFrame#label {{
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
        """Create simple header without frame"""
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
        label.setObjectName("label")
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
    
    def create_result_section(self):
        """Create result display section"""
        result_frame = QFrame()
        result_layout = QVBoxLayout()
        result_layout.setContentsMargins(15, 15, 15, 15)
        result_layout.setSpacing(10)
        
        variants_label = QLabel('Text Variants:')
        variants_label.setObjectName("label")
        variants_label.setFont(QFont('Arial', 11, QFont.Bold))
        result_layout.addWidget(variants_label)
        
        self.result_label = QLabel('')
        result_font = QFont('Arial', 18)
        self.result_label.setFont(result_font)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setWordWrap(True)
        self.result_label.setMinimumHeight(50)
        self.result_label.setStyleSheet("color: #8B0000;")
        result_layout.addWidget(self.result_label)
        
        images_label = QLabel('Image Variants:')
        images_label.setObjectName("label")
        images_label.setFont(QFont('Arial', 11, QFont.Bold))
        result_layout.addWidget(images_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(80)  # Smaller scroll area for small images
        scroll.setMaximumHeight(120)
        
        # Container for images with center alignment
        self.img_container = QWidget()
        self.img_layout = QHBoxLayout()
        self.img_layout.setContentsMargins(5, 5, 5, 5)
        self.img_layout.setSpacing(10)
        self.img_layout.addStretch()  # Add stretch at start
        self.img_container.setLayout(self.img_layout)
        
        scroll.setWidget(self.img_container)
        
        result_layout.addWidget(scroll)
        result_frame.setLayout(result_layout)
        return result_frame
    
    def create_footer(self):
        """Create footer with controls"""
        footer_frame = QFrame()
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 10, 15, 10)
        
        # info_label = QLabel('Chinese Character Dictionary | School Project 2024')
        # info_label.setStyleSheet("color: #8B4513; font-size: 9px;")
        # footer_layout.addWidget(info_label)
        
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
        """Search for character variants"""
        char = self.entry.text().strip()
        
        if not char:
            QMessageBox.warning(self, "Input Error", "Please enter a character.")
            return
        
        self.result_label.setText('')
        self.variant_pixmaps.clear()
        
        # Clear old images
        while self.img_layout.count() > 1:
            item = self.img_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        variants = get_variants(char)
        
        if not variants:
            QMessageBox.information(self, "Not Found", f"No variants found for '{char}'.")
            return
        
        text_only = [v for v, path in variants if v and not path]
        if text_only:
            self.result_label.setText(', '.join(text_only))
        
        image_count = 0
        for _, path in variants:
            if path and os.path.exists(path):
                try:
                    pixmap = QPixmap(path)
                    if not pixmap.isNull():
                        # Keep 45x45 size, no scaling needed
                        self.variant_pixmaps.append(pixmap)
                        
                        img_label = QLabel()
                        img_label.setPixmap(pixmap)
                        img_label.setFixedSize(45, 45)  # Add padding around image
                        img_label.setAlignment(Qt.AlignCenter)
                        img_label.setStyleSheet("""
                            border: 1px solid #8B4513;
                            padding: 5px;
                            background-color: #FFFACD;
                        """)
                        self.img_layout.insertWidget(image_count, img_label)
                        image_count += 1
                except Exception as e:
                    print(f"Error loading image: {e}")
        
        # Add stretch at the end for centering
        self.img_layout.addStretch()
    
    def clear_input(self):
        """Clear all inputs and results"""
        self.entry.clear()
        self.result_label.setText('')
        self.variant_pixmaps.clear()
        for w in self.img_container.findChildren(QLabel):
            w.deleteLater()
        self.entry.setFocus()
    
    def play_startup_music(self):
        """Play startup music on app launch"""
        music_file = r'E:\Benkyute Kudasai\Chinese\Building-a-dictionary-of-Chinese-variants\resources\China famous funny sound effect.mp3'
        
        if os.path.exists(music_file):
            try:
                media_content = QMediaContent(QUrl.fromLocalFile(music_file))
                self.media_player.setMedia(media_content)
                # self.media_player.play()
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