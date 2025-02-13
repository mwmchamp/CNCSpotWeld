import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
import svgwrite
import ezdxf

class VectorFileProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vector File to GCode Converter")
        self.setGeometry(100, 100, 800, 600)
        
        self.label = QLabel("Open a SVG or DXF file", self)
        self.label.setAlignment(Qt.AlignCenter)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        
        self.generate_button = QPushButton("Generate GCode", self)
        self.generate_button.clicked.connect(self.generate_gcode)
        self.layout.addWidget(self.generate_button)
        
        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)
        
        self.points = []
        
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
        # Load SVG and display it
        image = QImage(file_name)
        if image.isNull():
            self.label.setText("Failed to load SVG image.")
        else:
            pixmap = QPixmap.fromImage(image)
            self.label.setPixmap(pixmap)
            self.label.mousePressEvent = self.get_point

    def process_dxf(self, file_name):
        # Load DXF and display it
        doc = ezdxf.readfile(file_name)
        msp = doc.modelspace()
        # For simplicity, we assume the DXF is converted to an image for display
        # This part would require a more complex implementation to render DXF to an image
        # Here we just set a placeholder
        self.label.setText("DXF file loaded. Click to select points.")
        self.label.mousePressEvent = self.get_point

    def get_point(self, event):
        x = event.pos().x()
        y = event.pos().y()
        self.points.append((x, y))
        print(f"Point added: ({x}, {y})")

    def generate_gcode(self):
        if not self.points:
            print("No points selected. Please select points before generating GCode.")
            return
        with open("output.gcode", "w") as f:
            f.write("G21 ; Set units to millimeters\n")
            f.write("G90 ; Use absolute positioning\n")
            for point in self.points:
                f.write(f"G0 X{point[0]} Y{point[1]} ; Move to point\n")
                f.write("G38.2 Z-10 F100 ; Probe down\n")
                f.write("G0 Z5 ; Retract probe\n")
            f.write("M30 ; End of program\n")
        print("GCode generated successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VectorFileProcessor()
    window.show()
    sys.exit(app.exec_())
