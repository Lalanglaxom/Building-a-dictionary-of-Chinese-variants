import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
# Import the base class for the interceptor
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt5.QtCore import QUrl

# Step 1: Inherit from QWebEngineUrlRequestInterceptor
class NetworkInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        # Look for font extensions in the network traffic
        if any(ext in url.lower() for ext in ['.woff', '.woff2', '.ttf', '.otf']):
            print(f"\n[FONT DETECTED] --> {url}")
            
            # Check specifically for the MOE pattern
            if "/ttf/" in url:
                filename = url.split('/')[-1]
                print(f"   Target Filename found: {filename}")

class WebFontDebugger(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOE Font & Network Debugger")
        self.resize(1200, 800)

    def initUI(self, target_url):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.info = QLabel(f"Debugging URL: {target_url}")
        self.info.setStyleSheet("font-weight: bold; padding: 10px; background: #eee; border: 1px solid #ccc;")
        layout.addWidget(self.info)

        self.browser = QWebEngineView()
        
        # Step 2: Set up the interceptor and prevent Garbage Collection
        self.interceptor = NetworkInterceptor() # Store in self to keep it alive
        profile = QWebEngineProfile.defaultProfile()
        profile.setRequestInterceptor(self.interceptor)

        self.browser.load(QUrl(target_url))
        layout.addWidget(self.browser)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Plug in your MOE URL here
    TEST_URL = "https://dict.variants.moe.edu.tw/dictView.jsp?ID=115718"

    window = WebFontDebugger()
    window.initUI(TEST_URL)
    window.show()
    
    print(f"Browser started. Monitoring network requests for fonts...")
    sys.exit(app.exec_())