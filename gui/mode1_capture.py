"""Mode 1: General image capture interface."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont
import cv2
import os
from datetime import datetime
from camera import CameraManager

# Optional QR scanner support
try:
    from qr_scanner import QRScannerThread
    QR_SCANNER_AVAILABLE = True
except ImportError:
    QR_SCANNER_AVAILABLE = False
    QRScannerThread = None


class Mode1CaptureScreen(QWidget):
    """General purpose image and video capture interface."""
    
    def __init__(self, serial_number: str, description: str):
        super().__init__()
        self.serial_number = serial_number
        self.description = description
        self.current_camera = None
        self.is_recording = False
        self.video_writer = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.qr_scanner = None
        
        # Use "unknown" if no serial number provided
        output_serial = serial_number if serial_number else "unknown"
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "output", "captured_images", output_serial)
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"Output directory: {self.output_dir}")  # Show where files are saved
        
        self.init_ui()
        self.discover_cameras()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Mode 1: General Image Capture")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        info_label = QLabel(f"Serial: {self.serial_number if self.serial_number else 'Not Set'}")
        info_label.setFont(QFont("Arial", 10))
        header_layout.addWidget(info_label)
        layout.addLayout(header_layout)
        
        # QR Scanner status
        qr_layout = QHBoxLayout()
        qr_label = QLabel("QR Scanner:")
        qr_label.setFont(QFont("Arial", 10))
        self.qr_status_label = QLabel("Inactive")
        self.qr_status_label.setFont(QFont("Arial", 10))
        self.qr_status_label.setStyleSheet("color: gray;")
        self.qr_data_label = QLabel("")
        self.qr_data_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.qr_data_label.setStyleSheet("color: green;")
        qr_layout.addWidget(qr_label)
        qr_layout.addWidget(self.qr_status_label)
        qr_layout.addWidget(self.qr_data_label)
        qr_layout.addStretch()
        layout.addLayout(qr_layout)
        
        # Camera selection
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Camera:")
        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addStretch()
        layout.addLayout(camera_layout)
        
        # Camera preview
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(800, 600)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px solid black; background-color: #2b2b2b;")
        self.preview_label.setText("No camera selected")
        layout.addWidget(self.preview_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.setMinimumHeight(40)
        self.capture_button.clicked.connect(self.capture_image)
        self.capture_button.setEnabled(False)
        button_layout.addWidget(self.capture_button)
        
        self.record_button = QPushButton("Start Recording")
        self.record_button.setMinimumHeight(40)
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setEnabled(False)
        button_layout.addWidget(self.record_button)
        
        self.back_button = QPushButton("Back to Menu")
        self.back_button.setMinimumHeight(40)
        self.back_button.clicked.connect(self.close)
        button_layout.addWidget(self.back_button)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def discover_cameras(self):
        """Discover available cameras."""
        try:
            cameras = CameraManager.discover_cameras()
            
            self.camera_combo.clear()
            self.available_cameras = cameras
            
            for cam in cameras:
                self.camera_combo.addItem(cam.name)
            
            if not cameras:
                self.status_label.setText("No cameras found")
        except Exception as e:
            self.status_label.setText(f"Camera discovery error: {str(e)}")
            self.available_cameras = []
    
    def on_camera_changed(self, index):
        """Handle camera selection change."""
        try:
            # Stop existing QR scanner
            if self.qr_scanner:
                self.qr_scanner.stop()
                self.qr_scanner = None
            
            if self.current_camera:
                self.timer.stop()
                self.current_camera.close()
                self.current_camera = None
            
            if index >= 0 and index < len(self.available_cameras):
                self.current_camera = self.available_cameras[index]
                if self.current_camera.open():
                    self.timer.start(30)  # 30ms refresh
                    self.capture_button.setEnabled(True)
                    self.record_button.setEnabled(True)
                    self.status_label.setText(f"Connected to {self.current_camera.name}")
                    
                    # Start QR scanner if available
                    if QR_SCANNER_AVAILABLE:
                        self.qr_scanner = QRScannerThread(self.current_camera)
                        self.qr_scanner.qr_detected.connect(self.on_qr_detected)
                        self.qr_scanner.start()
                        self.qr_status_label.setText("Active")
                        self.qr_status_label.setStyleSheet("color: green;")
                    else:
                        self.qr_status_label.setText("Unavailable")
                        self.qr_status_label.setStyleSheet("color: gray;")
                else:
                    self.status_label.setText("Failed to open camera")
                    self.capture_button.setEnabled(False)
                    self.record_button.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"Camera error: {str(e)}")
            self.capture_button.setEnabled(False)
            self.record_button.setEnabled(False)
    
    def on_qr_detected(self, qr_data: str):
        """Handle QR code detection."""
        # Append to serial number if exists, otherwise set it
        if self.serial_number:
            self.serial_number = f"{self.serial_number}_{qr_data}"
        else:
            self.serial_number = qr_data
        
        self.qr_data_label.setText(f"Scanned: {qr_data}")
        self.status_label.setText(f"QR Code detected: {qr_data}")
        
        # Flash the QR data label
        QTimer.singleShot(3000, lambda: self.qr_data_label.setText(""))
    
    def update_frame(self):
        """Update camera preview."""
        if not self.current_camera:
            return
        
        frame = self.current_camera.capture_frame()
        if frame is not None:
            if self.is_recording and self.video_writer:
                self.video_writer.write(frame)
            
            # Convert to QImage for display
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Scale to fit preview
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.preview_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
    
    def capture_image(self):
        """Capture and save a single image."""
        if not self.current_camera:
            return
        
        frame = self.current_camera.capture_frame()
        if frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            serial_prefix = self.serial_number if self.serial_number else "unknown"
            filename = f"{serial_prefix}_{timestamp}.jpg"
            filepath = os.path.join(self.output_dir, filename)
            
            cv2.imwrite(filepath, frame)
            self.status_label.setText(f"Image saved: {filename}")
    
    def toggle_recording(self):
        """Start or stop video recording."""
        if not self.is_recording:
            # Start recording
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            serial_prefix = self.serial_number if self.serial_number else "unknown"
            filename = f"{serial_prefix}_{timestamp}.avi"
            filepath = os.path.join(self.output_dir, filename)
            
            width, height = self.current_camera.get_resolution()
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.video_writer = cv2.VideoWriter(filepath, fourcc, 20.0, (width, height))
            
            self.is_recording = True
            self.record_button.setText("Stop Recording")
            self.capture_button.setEnabled(False)
            self.status_label.setText(f"Recording: {filename}")
        else:
            # Stop recording
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            self.record_button.setText("Start Recording")
            self.capture_button.setEnabled(True)
            self.status_label.setText("Recording stopped")
    
    def closeEvent(self, event):
        """Clean up when closing."""
        try:
            self.timer.stop()
            if self.qr_scanner:
                self.qr_scanner.stop()
                self.qr_scanner.wait(1000)  # Wait up to 1 second for thread to finish
            if self.is_recording and self.video_writer:
                self.video_writer.release()
            if self.current_camera:
                self.current_camera.close()
        except Exception as e:
            print(f"Cleanup error: {e}")
        event.accept()
