import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView


class PDFViewer(QMainWindow):
    def __init__(self, pdf_path):
        super().__init__()

        self.central_widget = None
        self.webview = None
        self.pdf_path = pdf_path
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PDF Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)
        self.webview = QWebEngineView()
        layout.addWidget(self.webview)

        self.load_pdf()

    def load_pdf(self):
        url = QUrl.fromLocalFile(self.pdf_path)
        self.webview.setUrl(url)


def main():
    app = QApplication(sys.argv)
    pdf_path = "C:/temp/comanda.pdf"
    viewer = PDFViewer(pdf_path)
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
