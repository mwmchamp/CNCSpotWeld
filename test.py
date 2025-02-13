import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgRenderer
import ezdxf

class VectorFileViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vector File Viewer")
        self.setGeometry(100, 100, 800, 600)
        
        self.label = QLabel("Open a SVG or DXF file", self)
        self.label.setAlignment(Qt.AlignCenter)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        
        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)
        
        self.pixmap = None
        
        self.open_file()

    def open_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Vector File", "", "Vector Files (*.svg *.dxf);;All Files (*)", options=options)
        if file_name:
            if file_name.endswith('.svg'):
                self.process_svg(file_name)
            elif file_name.endswith('.dxf'):
                self.process_dxf(file_name)

    def process_svg(self, file_name):
        svg_renderer = QSvgRenderer(file_name)
        if not svg_renderer.isValid():
            self.label.setText("Failed to load SVG image.")
        else:
            pixmap = QPixmap(svg_renderer.defaultSize())
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            svg_renderer.render(painter)
            painter.end()
            self.pixmap = pixmap
            self.label.setPixmap(self.pixmap)

    def process_dxf(self, file_name):
        doc = ezdxf.readfile(file_name)
        msp = doc.modelspace()
        self.label.setText("DXF file loaded. Displaying is not implemented.")
        self.pixmap = QPixmap(800, 600)
        self.pixmap.fill(Qt.white)
        self.label.setPixmap(self.pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VectorFileViewer()
    window.show()
    sys.exit(app.exec_())
