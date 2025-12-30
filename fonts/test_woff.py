import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class WoffGridTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WOFF Font Grid Visualizer")
        self.resize(1200, 900)
        
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        # ======================================================================
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼   EDIT THIS LINE   ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        # ======================================================================

        # ### STEP 1: Type the character you want to test here.
        CHAR_TO_TEST = "󷂱"

        # ======================================================================
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲   END OF EDITING   ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        # ======================================================================

        base_path = os.path.dirname(os.path.abspath(__file__))

        # Lists to hold the CSS rules and the HTML boxes
        css_rules = []
        html_boxes = []
        
        # Get all font files
        files = sorted([f for f in os.listdir(base_path) if f.lower().endswith(('.woff', '.ttf'))])
        
        if not files:
            print("WARNING: No .woff or .ttf files found in this folder!")

        for filename in files:
            # Generate a unique internal font-family name for this specific file
            # e.g., "u6100.woff" becomes family "Font_u6100_woff"
            safe_name = filename.replace(".", "_").replace("-", "_")
            family_name = f"Font_{safe_name}"
            
            file_path = os.path.join(base_path, filename).replace('\\', '/')
            
            # 1. Generate CSS @font-face rule for this specific file
            rule = f"""
            @font-face {{
                font-family: '{family_name}';
                src: url('file:///{file_path}');
            }}
            """
            css_rules.append(rule)
            
            # 2. Generate the HTML Box for this specific file
            # We explicitly set the font-family to ONLY this file
            box = f"""
            <div class="box">
                <div class="filename">{filename}</div>
                <div class="char-display" style="font-family: '{family_name}';">
                    {CHAR_TO_TEST}
                </div>
            </div>
            """
            html_boxes.append(box)

        # Assemble the full HTML Page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                /* Inject all the generated @font-face rules */
                {''.join(css_rules)}

                body {{
                    background-color: #e0e0e0;
                    font-family: sans-serif;
                    padding: 20px;
                }}
                
                h1 {{
                    text-align: center;
                    color: #333;
                    margin-bottom: 20px;
                }}
                
                .grid-container {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    justify-content: center;
                }}
                
                .box {{
                    background: white;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    width: 140px;
                    height: 160px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                
                .filename {{
                    font-size: 11px;
                    color: #666;
                    background: #f0f0f0;
                    padding: 2px 6px;
                    border-radius: 4px;
                    margin-bottom: 10px;
                    max-width: 90%;
                    overflow: hidden;
                    white-space: nowrap;
                    text-overflow: ellipsis;
                }}
                
                .char-display {{
                    font-size: 64px;
                    color: #8B0000;
                    /* If the font file doesn't have the char, it will look generic or square */
                    line-height: 1;
                }}
            </style>
        </head>
        <body>
            <h1>Testing: {CHAR_TO_TEST} (U+{ord(CHAR_TO_TEST):X})</h1>
            <div class="grid-container">
                {''.join(html_boxes)}
            </div>
        </body>
        </html>
        """

        self.browser.setHtml(html_content, QUrl.fromLocalFile(base_path))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WoffGridTester()
    window.show()
    sys.exit(app.exec_())