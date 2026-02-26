"""Mode 1: General image capture interface."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QFileDialog, QMessageBox, QLineEdit, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont
import cv2
import os
import json
import numpy as np
from datetime import datetime
from camera import CameraManager
from reports import generate_reports
from gui.annotatable_preview import AnnotatablePreview

# Optional QR scanner support
try:
    from qr_scanner import QRScannerThread
    QR_SCANNER_AVAILABLE = True
except ImportError:
    QR_SCANNER_AVAILABLE = False
    QRScannerThread = None


class Mode1CaptureScreen(QWidget):
    """General purpose image and video capture interface."""
    
    back_requested = pyqtSignal()  # Signal to request return to menu
    
    def __init__(self, serial_number: str, technician: str, description: str):
        super().__init__()
        self.serial_number = serial_number
        self.technician = technician
        self.description = description
        self.current_camera = None
        self.is_recording = False
        self.video_writer = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.qr_scanner = None
        self.barcode_check_timer = None
        self.captured_images = []  # List of dicts: {path, camera, notes, barcode_scans}
        self.report_generated = False  # Track if report has been generated
        self.barcode_scans = []  # List of dicts: {type, data, timestamp}
        
        # Use "unknown" if no serial number provided - sanitize for filesystem
        output_serial = self._sanitize_filename(serial_number) if serial_number else "unknown"
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "output", "captured_images", output_serial)
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"Output directory: {self.output_dir}")  # Show where files are saved
        
        self.init_ui()
        self.discover_cameras()
    
    def _sanitize_filename(self, filename):
        """Remove invalid characters from filename."""
        # Windows invalid characters: < > : " / \ | ? *
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # Also remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        return filename if filename else "unknown"
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with green background and back button
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            background-color: #77C25E;
            border-radius: 5px;
            padding: 10px;
        """)
        header_layout = QHBoxLayout(header_widget)
        
        title = QLabel("Mode 1: General Image Capture")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        info_label = QLabel(f"Serial: {self.serial_number if self.serial_number else 'Not Set'}")
        info_label.setFont(QFont("Arial", 10))
        info_label.setStyleSheet("color: white; background: transparent;")
        header_layout.addWidget(info_label)
        
        # Back button in header
        self.back_button = QPushButton("Back to Menu")
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        self.back_button.clicked.connect(self.on_back_clicked)
        header_layout.addWidget(self.back_button)
        
        layout.addWidget(header_widget)
        
        # QR Scanner status
        qr_layout = QHBoxLayout()
        qr_label = QLabel("Barcode Scanner:")
        qr_label.setFont(QFont("Arial", 10))
        self.qr_status_label = QLabel("Inactive")
        self.qr_status_label.setFont(QFont("Arial", 10))
        self.qr_status_label.setStyleSheet("color: gray;")
        self.qr_data_label = QLabel("")
        self.qr_data_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.qr_data_label.setStyleSheet("color: #77C25E;")
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
        
        # Annotatable camera preview
        self.preview_label = AnnotatablePreview()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px solid black; background-color: #2b2b2b;")
        self.preview_label.setText("No camera selected")
        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        layout.addWidget(self.preview_label)
        
        # Capture/Scan/Record buttons directly below camera
        button_layout = QHBoxLayout()
        
        # Button stylesheet
        button_style = """
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
            QPushButton:pressed {
                background-color: #4D8A3C;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """
        
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.setMinimumHeight(40)
        self.capture_button.setStyleSheet(button_style)
        self.capture_button.clicked.connect(self.capture_image)
        self.capture_button.setEnabled(False)
        button_layout.addWidget(self.capture_button)
        
        self.scan_button = QPushButton("Scan Barcode/QR")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setMaximumWidth(150)
        self.scan_button.setStyleSheet(button_style)
        self.scan_button.clicked.connect(self.scan_barcode)
        self.scan_button.setEnabled(False)
        button_layout.addWidget(self.scan_button)
        
        self.record_button = QPushButton("Start Recording")
        self.record_button.setMinimumHeight(40)
        self.record_button.setStyleSheet(button_style)
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setEnabled(False)
        button_layout.addWidget(self.record_button)
        
        layout.addLayout(button_layout)
        
        # Annotation controls
        annotation_layout = QHBoxLayout()
        annotation_label = QLabel("Annotations:")
        annotation_label.setStyleSheet("font-weight: bold;")
        
        self.clear_markers_button = QPushButton("Clear Markers")
        self.clear_markers_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF5252;
            }
        """)
        self.clear_markers_button.clicked.connect(self.preview_label.clear_markers)
        
        annotation_help = QLabel("Left-click: Add | Drag: Move | Scroll: Rotate | Shift+Scroll: Length | Right-click: Remove")
        annotation_help.setStyleSheet("color: #666666; font-size: 10px;")
        
        annotation_layout.addWidget(annotation_label)
        annotation_layout.addWidget(self.clear_markers_button)
        annotation_layout.addWidget(annotation_help)
        annotation_layout.addStretch()
        layout.addLayout(annotation_layout)
        
        # Image notes input (optional)
        notes_layout = QHBoxLayout()
        notes_label = QLabel("Image Notes (optional):")
        notes_label.setStyleSheet("font-weight: bold;")
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Add notes for the next captured image...")
        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(self.notes_input)
        layout.addLayout(notes_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def discover_cameras(self):
        """Discover available cameras."""
        self.status_label.setText("Discovering cameras...")
        try:
            cameras = CameraManager.discover_cameras()
            
            # Close all cameras after discovery - they'll be reopened when selected
            for cam in cameras:
                cam.close()
            
            self.camera_combo.clear()
            self.available_cameras = cameras
            
            for cam in cameras:
                self.camera_combo.addItem(cam.name)
            
            if not cameras:
                self.status_label.setText("No cameras found")
            else:
                self.status_label.setText(f"Found {len(cameras)} camera(s)")
        except Exception as e:
            self.status_label.setText(f"Camera discovery error: {str(e)}")
            self.available_cameras = []
    
    def on_camera_changed(self, index):
        """Handle camera selection change."""
        try:
            # Stop timer first to prevent frame updates during switch
            self.timer.stop()
            
            # Stop existing QR scanner before closing camera
            if self.qr_scanner:
                print("Stopping QR scanner...")
                self.qr_scanner.stop()
                self.qr_scanner = None
                print("QR scanner stopped")
            
            if self.current_camera:
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
                        print("Starting barcode scanner...")
                        self.qr_scanner = QRScannerThread(self.current_camera)
                        self.qr_scanner.barcode_detected.connect(self.on_barcode_detected)
                        self.qr_scanner.start()
                        self.qr_status_label.setText("Active")
                        self.qr_status_label.setStyleSheet("color: #77C25E;")
                        # Start timer to check barcode availability
                        self.barcode_check_timer = QTimer()
                        self.barcode_check_timer.timeout.connect(self.update_scan_button_state)
                        self.barcode_check_timer.start(100)
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
    
    def on_barcode_detected(self, barcode_type: str, barcode_data: str):
        """Handle barcode detection (just update status, don't auto-append)."""
        self.qr_data_label.setText(f"Detected: {barcode_type}")
        self.status_label.setText(f"Barcode detected: {barcode_data[:50]}...")
    
    def update_scan_button_state(self):
        """Enable/disable scan button based on barcode detection."""
        if self.qr_scanner:
            barcode_type, barcode_data = self.qr_scanner.get_current_barcode()
            self.scan_button.setEnabled(barcode_type is not None)
    
    def scan_barcode(self):
        """Capture current barcode scan."""
        if not self.qr_scanner:
            return
        
        barcode_type, barcode_data = self.qr_scanner.get_current_barcode()
        if not barcode_type or not barcode_data:
            return
        
        # Add to scans list
        scan_info = {
            'type': barcode_type,
            'data': barcode_data,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.barcode_scans.append(scan_info)
        
        # Capture current frame
        if self.current_camera:
            frame = self.current_camera.capture_frame()
            if frame is not None:
                # Save image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"barcode_scan_{timestamp}.jpg"
                filepath = os.path.join(self.output_dir, filename)
                cv2.imwrite(filepath, frame)
                
                # Add to captured images with barcode note
                self.captured_images.append({
                    'path': filepath,
                    'camera': self.current_camera.name,
                    'notes': f"Barcode scan capture ({barcode_type}): {barcode_data}",
                    'barcode_scans': [scan_info]
                })
        
        # Show dialog
        scan_count = len(self.barcode_scans)
        msg = QMessageBox(self)
        msg.setWindowTitle("Barcode Scanned")
        msg.setText(f"Barcode Type: {barcode_type}\nData: {barcode_data}\n\nScan {scan_count} for this session")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
        
        self.status_label.setText(f"Barcode scanned ({scan_count} total)")
    
    def update_frame(self):
        """Update camera preview."""
        if not self.current_camera:
            return
        
        frame = self.current_camera.capture_frame()
        if frame is not None:
            if self.is_recording and self.video_writer:
                # Draw markers on frame for video
                annotated_frame = frame.copy()
                if self.preview_label.markers:
                    annotated_frame = self._draw_markers_on_frame(annotated_frame, self.preview_label.markers)
                self.video_writer.write(annotated_frame)
            
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
            self.preview_label.set_frame(scaled_pixmap)
    
    def capture_image(self):
        """Capture and save a single image with annotations."""
        if not self.current_camera:
            return
        
        frame = self.current_camera.capture_frame()
        if frame is not None:
            # Get markers before saving
            markers = self.preview_label.get_markers_data()
            
            # Draw markers on the frame if any exist
            if markers:
                frame = self._draw_markers_on_frame(frame, markers)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            serial_prefix = self.serial_number if self.serial_number else "unknown"
            filename = f"{serial_prefix}_{timestamp}.jpg"
            filepath = os.path.join(self.output_dir, filename)
            
            cv2.imwrite(filepath, frame)
            
            # Get notes and camera info
            notes = self.notes_input.text().strip()
            camera_name = self.current_camera.name if self.current_camera else "Unknown"
            
            # Store image with metadata including markers
            image_data = {
                'path': filepath,
                'camera': camera_name,
                'notes': notes,
                'timestamp': timestamp,
                'type': 'image',
                'markers': markers
            }
            self.captured_images.append(image_data)
            
            # Save metadata to JSON file alongside image
            self._save_metadata_file(filepath, image_data)
            
            # Clear notes and markers for next image
            self.notes_input.clear()
            self.preview_label.clear_markers()
            
            self.status_label.setText(f"Image saved: {filename} (Total: {len(self.captured_images)})")
    
    def _draw_markers_on_frame(self, frame, markers):
        """Draw annotation markers on the frame."""
        frame_h, frame_w = frame.shape[:2]
        
        for marker in markers:
            # Markers are now stored as relative coordinates (0-1)
            x = int(marker['x'] * frame_w)
            y = int(marker['y'] * frame_h)
            label = marker['label']
            angle = marker.get('angle', 45)
            arrow_length = marker.get('length', 30)
            
            # Draw arrow with rotation
            angle_rad = np.radians(angle)
            end_x = int(x + arrow_length * np.cos(angle_rad))
            end_y = int(y + arrow_length * np.sin(angle_rad))
            
            # Arrow line
            cv2.arrowedLine(frame, (x, y), (end_x, end_y), (0, 0, 255), 2, tipLength=0.3)
            
            # Label circle at arrow tip
            cv2.circle(frame, (end_x, end_y), 12, (255, 255, 255), -1)
            cv2.circle(frame, (end_x, end_y), 12, (0, 0, 255), 2)
            
            # Label text
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(label, font, 0.5, 2)[0]
            text_x = end_x - text_size[0] // 2
            text_y = end_y + text_size[1] // 2
            cv2.putText(frame, label, (text_x, text_y), font, 0.5, (0, 0, 255), 2)
        
        return frame
    
    def _save_metadata_file(self, media_path, metadata):
        """Save metadata JSON file alongside media file."""
        json_path = os.path.splitext(media_path)[0] + '_metadata.json'
        try:
            with open(json_path, 'w') as f:
                json.dump({
                    'filename': os.path.basename(media_path),
                    'camera': metadata.get('camera', 'Unknown'),
                    'notes': metadata.get('notes', ''),
                    'timestamp': metadata.get('timestamp', ''),
                    'type': metadata.get('type', 'image'),
                    'markers': metadata.get('markers', []),
                    'serial_number': self.serial_number,
                    'description': self.description
                }, f, indent=2)
        except Exception as e:
            print(f"Failed to save metadata: {e}")
    
    def toggle_recording(self):
        """Start or stop video recording."""
        if not self.is_recording:
            # Start recording
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            serial_prefix = self.serial_number if self.serial_number else "unknown"
            filename = f"{serial_prefix}_{timestamp}.mp4"
            filepath = os.path.join(self.output_dir, filename)
            
            width, height = self.current_camera.get_resolution()
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(filepath, fourcc, 20.0, (width, height))
            
            # Store video start info
            self.current_video_path = filepath
            self.current_video_timestamp = timestamp
            
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
            
            # Get notes, camera info, and markers for video
            notes = self.notes_input.text().strip()
            camera_name = self.current_camera.name if self.current_camera else "Unknown"
            markers = self.preview_label.get_markers_data()
            
            # Store video with metadata
            video_data = {
                'path': self.current_video_path,
                'camera': camera_name,
                'notes': notes,
                'timestamp': self.current_video_timestamp,
                'type': 'video',
                'markers': markers
            }
            self.captured_images.append(video_data)
            
            # Save metadata to JSON file alongside video
            self._save_metadata_file(self.current_video_path, video_data)
            
            # Clear notes and markers
            self.notes_input.clear()
            self.preview_label.clear_markers()
            
            self.record_button.setText("Start Recording")
            self.capture_button.setEnabled(True)
            self.status_label.setText(f"Recording stopped (Total: {len(self.captured_images)})")
    
    def on_back_clicked(self):
        """Handle back button click."""
        # Auto-generate report if images were captured
        if self.captured_images and not self.report_generated:
            try:
                self.status_label.setText("Generating reports...")
                pdf_path, docx_path = generate_reports(
                    self.serial_number,
                    self.technician,
                    self.description,
                    self.captured_images,
                    barcode_scans=self.barcode_scans
                )
                self.report_generated = True
                self.status_label.setText(f"✓ Reports saved")
                
                # Show success dialog
                QMessageBox.information(
                    self,
                    "Reports Generated",
                    f"PDF and DOCX reports generated successfully!\n\n"
                    f"PDF: {pdf_path}\n\n"
                    f"DOCX: {docx_path}\n\n"
                    f"Images included: {len(self.captured_images)}"
                )
            except Exception as e:
                # Show error but don't block exit
                QMessageBox.warning(
                    self,
                    "Report Error",
                    f"Failed to generate report:\n{str(e)}"
                )
                print(f"Report generation error: {e}")
        
        self.cleanup_resources()
        self.back_requested.emit()
    
    def cleanup_resources(self):
        """Clean up resources before closing."""
        # Stop timer immediately
        if self.timer.isActive():
            self.timer.stop()
        
        # Stop barcode check timer
        if self.barcode_check_timer and self.barcode_check_timer.isActive():
            self.barcode_check_timer.stop()
        
        # Stop recording if active
        if self.is_recording and self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        # Stop QR scanner without waiting
        if self.qr_scanner:
            self.qr_scanner.stop()
            self.qr_scanner = None
        
        # Close camera
        if self.current_camera:
            self.current_camera.close()
            self.current_camera = None
    
    def closeEvent(self, event):
        """Clean up when closing."""
        # Auto-generate report if images were captured
        if self.captured_images and not self.report_generated:
            try:
                pdf_path, docx_path = generate_reports(
                    self.serial_number,
                    self.technician,
                    self.description,
                    self.captured_images,
                    barcode_scans=self.barcode_scans
                )
                self.report_generated = True
                
                # Show success dialog
                QMessageBox.information(
                    self,
                    "Reports Generated",
                    f"PDF and DOCX reports generated successfully!\n\n"
                    f"PDF: {pdf_path}\n\n"
                    f"DOCX: {docx_path}\n\n"
                    f"Images included: {len(self.captured_images)}"
                )
            except Exception as e:
                # Show error but don't block exit
                QMessageBox.warning(
                    self,
                    "Report Error",
                    f"Failed to generate report:\n{str(e)}"
                )
                print(f"Report generation error: {e}")
        
        self.cleanup_resources()
        event.accept()
