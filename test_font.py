import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class FontTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple WOFF Tester")
        self.resize(800, 600)

        # Create the Web Browser Widget
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        # ======================================================================
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼   EDIT YOUR SETTINGS BELOW   ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        # ======================================================================

        # ### STEP 1: Write the exact filename of your font here.
        # Make sure this file is in the SAME FOLDER as this script.
        # Example: "u6100.woff" or "u6100.ttf"
        FONT_FILENAME = "uf6f00.woff" 

        # ### STEP 2: Paste the character you want to test here.
        # Make sure this character actually exists inside that specific font file.
        CHAR_TO_TEST = "󶗆"

        # ======================================================================
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲   END OF USER SETTINGS   ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        # ======================================================================

        # 1. Calculate the absolute path for the web engine
        # We need forward slashes (/) for CSS to work on Windows
        base_path = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(base_path, FONT_FILENAME).replace('\\', '/')

        # 2. Create the HTML with CSS @font-face
        # We define a custom font family named 'MyTestFont' pointing to your file
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @font-face {{
                    font-family: 'MyTestFont';
                    src: url('file:///{font_path}');
                }}

                body {{
                    background-color: #f0f0f0;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    font-family: sans-serif;
                }}

                .box {{
                    border: 2px dashed #8B0000;
                    padding: 40px;
                    background: white;
                    text-align: center;
                }}

                .test-char {{
                    /* Apply the custom font here */
                    font-family: 'MyTestFont'; 
                    font-size: 100px;
                    color: #8B0000;
                    margin: 20px 0;
                }}
                
                .info {{ color: #555; }}
            </style>
        </head>
        <body>
            <div class="box">
                <div class="info">Testing File: <b>{FONT_FILENAME}</b></div>
                
                <div class="test-char">{CHAR_TO_TEST}</div>
                
                <div class="info">Unicode: U+{ord(CHAR_TO_TEST):X}</div>
            </div>
        </body>
        </html>
        """

        # 3. Load the HTML
        # We pass the base URL so it can resolve local files if needed
        self.browser.setHtml(html_content, QUrl.fromLocalFile(base_path))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FontTester()
    window.show()
    sys.exit(app.exec_())