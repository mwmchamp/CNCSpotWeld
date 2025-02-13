import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt
from PyQt5.QtSvg import QSvgRenderer
import ezdxf

class CNCMachineGCodeGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNC Machine GCode Generator")
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
            self.label.mousePressEvent = self.get_point

    def process_dxf(self, file_name):
        try:
            doc = ezdxf.readfile(file_name)
            msp = doc.modelspace()
            
            bounds = None
            for entity in msp:
                if hasattr(entity, 'get_bbox'):
                    current_bounds = entity.get_bbox()
                    if bounds is None:
                        bounds = current_bounds
                    else:
                        bounds = (
                            min(bounds[0], current_bounds[0]),
                            min(bounds[1], current_bounds[1]),
                            max(bounds[2], current_bounds[2]),
                            max(bounds[3], current_bounds[3])
                        )
            
            if bounds is None:
                self.label.setText("No drawable entities found in DXF")
                return
                
            width, height = 800, 600
            self.pixmap = QPixmap(width, height)
            self.pixmap.fill(Qt.white)
            
            dxf_width = bounds[2] - bounds[0]
            dxf_height = bounds[3] - bounds[1]
            scale_x = (width - 40) / dxf_width
            scale_y = (height - 40) / dxf_height
            scale = min(scale_x, scale_y)
            
            offset_x = (width - dxf_width * scale) / 2
            offset_y = (height - dxf_height * scale) / 2
            
            painter = QPainter(self.pixmap)
            painter.setPen(QPen(Qt.black, 1))
            
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    x1 = (start[0] - bounds[0]) * scale + offset_x
                    y1 = height - ((start[1] - bounds[1]) * scale + offset_y)
                    x2 = (end[0] - bounds[0]) * scale + offset_x
                    y2 = height - ((end[1] - bounds[1]) * scale + offset_y)
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                elif entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    x = (center[0] - bounds[0]) * scale + offset_x
                    y = height - ((center[1] - bounds[1]) * scale + offset_y)
                    r = radius * scale
                    painter.drawEllipse(QPointF(x, y), r, r)
            
            painter.end()
            self.label.setPixmap(self.pixmap)
            self.label.mousePressEvent = self.get_point
            
            self.dxf_transform = {
                'scale': scale,
                'bounds': bounds,
                'offset_x': offset_x,
                'offset_y': offset_y,
                'height': height
            }
            
        except Exception as e:
            self.label.setText(f"Error loading DXF: {str(e)}")

    def get_point(self, event):
        x = event.pos().x()
        y = event.pos().y()
        
        self.points.append((x, y))
        print(f"Point added at screen coordinates: ({x}, {y})")
        
        if hasattr(self, 'dxf_transform'):
            dxf_x = (x - self.dxf_transform['offset_x']) / self.dxf_transform['scale'] + self.dxf_transform['bounds'][0]
            dxf_y = (self.dxf_transform['height'] - y - self.dxf_transform['offset_y']) / self.dxf_transform['scale'] + self.dxf_transform['bounds'][1]
            print(f"DXF coordinates: ({dxf_x:.2f}, {dxf_y:.2f})")
        
        self.update_image_with_points()

    def update_image_with_points(self):
        if self.pixmap:
            overlay = self.pixmap.copy()
            painter = QPainter(overlay)
            
            point_size = 6
            painter.setPen(QPen(Qt.red, 2))
            painter.setBrush(QColor(255, 0, 0, 127))
            
            for point in self.points:
                painter.drawEllipse(point[0] - point_size//2, point[1] - point_size//2, 
                                  point_size, point_size)
                painter.drawText(point[0] + point_size, point[1] + point_size, 
                               str(self.points.index(point) + 1))
            
            painter.end()
            self.label.setPixmap(overlay)

    def generate_gcode(self):
        if not self.points:
            print("No points selected. Please select points before generating GCode.")
            return

        # Function to calculate the Euclidean distance between two points
        def distance(p1, p2):
            return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

        # Use a simple nearest neighbor algorithm to order points for minimal travel
        if self.points:
            ordered_points = [self.points[0]]
            remaining_points = self.points[1:]

            while remaining_points:
                last_point = ordered_points[-1]
                next_point = min(remaining_points, key=lambda p: distance(last_point, p))
                ordered_points.append(next_point)
                remaining_points.remove(next_point)

        with open("output.gcode", "w") as f:
            f.write("G21 ; Set units to millimeters\n")
            f.write("G90 ; Use absolute positioning\n")

            for i, point in enumerate(ordered_points, 1):
                if hasattr(self, 'dxf_transform'):
                    x = (point[0] - self.dxf_transform['offset_x']) / self.dxf_transform['scale'] + self.dxf_transform['bounds'][0]
                    y = (self.dxf_transform['height'] - point[1] - self.dxf_transform['offset_y']) / self.dxf_transform['scale'] + self.dxf_transform['bounds'][1]
                else:
                    x, y = point

                f.write(f"; Point {i}\n")
                f.write(f"G0 X{x:.3f} Y{y:.3f} ; Move to point\n")
                f.write("G38.2 Z-10 F100 ; Probe down\n")
                f.write("G0 Z5 ; Retract probe\n")

            f.write("M30 ; End of program\n")
        print("GCode generated successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CNCMachineGCodeGenerator()
    window.show()
    sys.exit(app.exec_())
