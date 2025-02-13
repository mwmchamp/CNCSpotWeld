import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QPointF, QRectF
import svgwrite
import ezdxf
from PyQt5.QtSvg import QSvgRenderer

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
        # Load SVG and display it using QSvgRenderer
        svg_renderer = QSvgRenderer(file_name)
        if not svg_renderer.isValid():
            self.label.setText("Failed to load SVG image.")
        else:
            # Create a QPixmap with the size of the SVG
            pixmap = QPixmap(svg_renderer.defaultSize())
            pixmap.fill(Qt.transparent)  # Fill with transparent background
            painter = QPainter(pixmap)
            svg_renderer.render(painter)
            painter.end()
            self.pixmap = pixmap
            self.label.setPixmap(self.pixmap)
            self.label.mousePressEvent = self.get_point

    def process_dxf(self, file_name):
        try:
            # Load DXF file
            doc = ezdxf.readfile(file_name)
            msp = doc.modelspace()
            
            # Get the bounds of all entities
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
                
            # Create a pixmap to draw on
            width, height = 800, 600  # Default size
            self.pixmap = QPixmap(width, height)
            self.pixmap.fill(Qt.white)
            
            # Calculate scale factor to fit the drawing
            dxf_width = bounds[2] - bounds[0]
            dxf_height = bounds[3] - bounds[1]
            scale_x = (width - 40) / dxf_width  # Leave some margin
            scale_y = (height - 40) / dxf_height
            scale = min(scale_x, scale_y)
            
            # Calculate offset to center the drawing
            offset_x = (width - dxf_width * scale) / 2
            offset_y = (height - dxf_height * scale) / 2
            
            # Draw entities
            painter = QPainter(self.pixmap)
            painter.setPen(QPen(Qt.black, 1))
            
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    # Transform coordinates
                    x1 = (start[0] - bounds[0]) * scale + offset_x
                    y1 = height - ((start[1] - bounds[1]) * scale + offset_y)
                    x2 = (end[0] - bounds[0]) * scale + offset_x
                    y2 = height - ((end[1] - bounds[1]) * scale + offset_y)
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                elif entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    # Transform coordinates
                    x = (center[0] - bounds[0]) * scale + offset_x
                    y = height - ((center[1] - bounds[1]) * scale + offset_y)
                    r = radius * scale
                    painter.drawEllipse(QPointF(x, y), r, r)
                # Add more entity types as needed
            
            painter.end()
            self.label.setPixmap(self.pixmap)
            self.label.mousePressEvent = self.get_point
            
            # Store transformation parameters for point conversion
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
        
        # Store the screen coordinates
        self.points.append((x, y))
        print(f"Point added at screen coordinates: ({x}, {y})")
        
        # If we have DXF transformation data, calculate the actual DXF coordinates
        if hasattr(self, 'dxf_transform'):
            # Reverse transform to get DXF coordinates
            dxf_x = (x - self.dxf_transform['offset_x']) / self.dxf_transform['scale'] + self.dxf_transform['bounds'][0]
            dxf_y = (self.dxf_transform['height'] - y - self.dxf_transform['offset_y']) / self.dxf_transform['scale'] + self.dxf_transform['bounds'][1]
            print(f"DXF coordinates: ({dxf_x:.2f}, {dxf_y:.2f})")
        
        self.update_image_with_points()

    def update_image_with_points(self):
        if self.pixmap:
            overlay = self.pixmap.copy()
            painter = QPainter(overlay)
            
            # Set up the point appearance
            point_size = 6  # Larger point size
            painter.setPen(QPen(Qt.red, 2))  # Thicker red outline
            painter.setBrush(QColor(255, 0, 0, 127))  # Semi-transparent red fill
            
            for point in self.points:
                # Draw a more visible point
                painter.drawEllipse(point[0] - point_size//2, point[1] - point_size//2, 
                                  point_size, point_size)
                
                # Add a small label with point number
                painter.drawText(point[0] + point_size, point[1] + point_size, 
                               str(self.points.index(point) + 1))
            
            painter.end()
            self.label.setPixmap(overlay)

    def generate_gcode(self):
        if not self.points:
            print("No points selected. Please select points before generating GCode.")
            return
            
        with open("output.gcode", "w") as f:
            f.write("G21 ; Set units to millimeters\n")
            f.write("G90 ; Use absolute positioning\n")
            
            for i, point in enumerate(self.points, 1):
                if hasattr(self, 'dxf_transform'):
                    # Convert screen coordinates to DXF coordinates
                    x = (point[0] - self.dxf_transform['offset_x']) / self.dxf_transform['scale'] + self.dxf_transform['bounds'][0]
                    y = (self.dxf_transform['height'] - point[1] - self.dxf_transform['offset_y']) / self.dxf_transform['scale'] + self.dxf_transform['bounds'][1]
                else:
                    # If no DXF transform, use screen coordinates directly
                    x, y = point
                
                f.write(f"; Point {i}\n")
                f.write(f"G0 X{x:.3f} Y{y:.3f} ; Move to point\n")
                f.write("G38.2 Z-10 F100 ; Probe down\n")
                f.write("G0 Z5 ; Retract probe\n")
            
            f.write("M30 ; End of program\n")
        print("GCode generated successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VectorFileProcessor()
    window.show()
    sys.exit(app.exec_())
