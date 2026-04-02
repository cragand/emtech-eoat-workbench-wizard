"""Mode 1: General image capture interface."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QFileDialog, QMessageBox, QLineEdit, QSizePolicy,
                             QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont
import cv2
import os
import json
import numpy as np
import subprocess
import platform
from datetime import datetime
from camera import CameraManager
from reports import generate_reports
from logger_config import get_logger

logger = get_logger(__name__)
from gui.annotatable_preview import AnnotatablePreview
from gui.review_captures_dialog import ReviewCapturesDialog
from gui.camera_settings_dialog import CameraSettingsDialog
from gui.mask_editor import MaskEditorDialog
from gui.capture_review_dialog import CaptureReviewDialog

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
    
    def __init__(self, serial_number: str, technician: str, description: str, cached_cameras=None, audit=None):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.serial_number = serial_number
        self.technician = technician
        self.description = description
        self.audit = audit
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
        self.overlay_path = None  # Path to active overlay PNG
        self._overlay_cache = None  # Cached BGRA overlay image (raw, unscaled)
        self._overlay_cache_size = None  # (w, h) the cache was scaled to
        self._overlay_cache_scaled = None  # Pre-scaled alpha and BGR arrays
        self._consecutive_frame_failures = 0
        
        # Use cached cameras if provided, otherwise discover
        self.available_cameras = cached_cameras if cached_cameras is not None else []
        
        # Use "unknown" if no serial number provided - sanitize for filesystem
        output_serial = self._sanitize_filename(serial_number) if serial_number else "unknown"
        from preferences_manager import preferences as _prefs
        self._prefs = _prefs
        self.output_dir = os.path.join(_prefs.get_captured_images_dir(), output_serial)
        os.makedirs(self.output_dir, exist_ok=True)
        self._reports_dir = _prefs.get_reports_dir()
        
        logger.info(f"Output directory: {self.output_dir}")
        
        # Warn if custom paths fell back to defaults (e.g. network share unavailable)
        self._path_fallback_warnings = []
        if _prefs.is_captured_images_dir_fallback():
            self._path_fallback_warnings.append(
                f"⚠️ Custom images folder is unavailable.\nImages will be saved locally to:\n{self.output_dir}")
        if _prefs.is_reports_dir_fallback():
            self._path_fallback_warnings.append(
                f"⚠️ Custom reports folder is unavailable.\nReports will be saved locally to:\n{self._reports_dir}")
        
        self.init_ui()
        
        # Only discover cameras if not already cached
        if not self.available_cameras:
            self.discover_cameras()
        else:
            logger.info(f"Using {len(self.available_cameras)} cached camera(s)")
            self.camera_combo.clear()
            for cam in self.available_cameras:
                self.camera_combo.addItem(cam.name)
        
        # Set focus to this widget so keyboard shortcuts work immediately
        self.setFocus()
        
        # Show path fallback warnings after UI is visible
        if self._path_fallback_warnings:
            QTimer.singleShot(200, self._show_path_fallback_warnings)
    
    def _show_path_fallback_warnings(self):
        """Show warnings about custom output paths that fell back to defaults."""
        QMessageBox.warning(self, "Output Path Unavailable",
                            "\n\n".join(self._path_fallback_warnings))
        self._path_fallback_warnings.clear()
    
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
        
        # Serial number in center
        info_label = QLabel(f"Serial: {self.serial_number if self.serial_number else 'Not Set'}")
        info_label.setFont(QFont("Arial", 12))
        info_label.setStyleSheet("color: white; background: transparent;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(info_label)
        
        # Back button on right
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
        self.back_button.setFocusPolicy(Qt.NoFocus)
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
        
        # Camera settings button
        self.camera_settings_button = QPushButton("⚙️ Settings")
        self.camera_settings_button.setMaximumWidth(100)
        self.camera_settings_button.setFocusPolicy(Qt.NoFocus)
        self.camera_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.camera_settings_button.clicked.connect(self.open_camera_settings)
        camera_layout.addWidget(self.camera_settings_button)
        
        camera_layout.addStretch()
        layout.addLayout(camera_layout)
        
        # Tools row above camera preview
        review_layout = QHBoxLayout()
        
        # Overlay mask editor button
        self.mask_editor_button = QPushButton("🎭 Create Overlay Mask")
        self.mask_editor_button.setMaximumWidth(200)
        self.mask_editor_button.setFocusPolicy(Qt.NoFocus)
        self.mask_editor_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.mask_editor_button.clicked.connect(self.open_mask_editor)
        review_layout.addWidget(self.mask_editor_button)
        
        review_layout.addStretch()
        self.review_button = QPushButton("📋 Review Captures")
        self.review_button.setMaximumWidth(180)
        self.review_button.setFocusPolicy(Qt.NoFocus)
        self.review_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.review_button.clicked.connect(self.open_review_dialog)
        review_layout.addWidget(self.review_button)
        layout.addLayout(review_layout)
        
        # Annotatable camera preview
        self.preview_label = AnnotatablePreview()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px solid black; background-color: #2b2b2b;")
        self.preview_label.setText("No camera selected")
        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        layout.addWidget(self.preview_label)
        
        # Capture/Scan/Record buttons below camera
        button_layout = QHBoxLayout()
        
        self.capture_button = QPushButton("Capture Image (Space)")
        self.capture_button.setMinimumHeight(40)
        self.capture_button.setFocusPolicy(Qt.NoFocus)
        self.capture_button.setToolTip("Capture an image from the camera (Space)")
        self.capture_button.clicked.connect(self.capture_image)
        self.capture_button.setEnabled(False)
        button_layout.addWidget(self.capture_button)
        
        self.scan_button = QPushButton("Scan Barcode/QR (B)")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setMaximumWidth(180)
        self.scan_button.setFocusPolicy(Qt.NoFocus)
        self.scan_button.setToolTip("Scan a barcode or QR code (B)")
        self.scan_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.scan_button.clicked.connect(self.scan_barcode)
        self.scan_button.setEnabled(False)
        button_layout.addWidget(self.scan_button)
        
        self.record_button = QPushButton("🔴 Start Recording (R)")
        self.record_button.setMinimumHeight(40)
        self.record_button.setFocusPolicy(Qt.NoFocus)
        self.record_button.setToolTip("Start/stop video recording (R)")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setEnabled(False)
        button_layout.addWidget(self.record_button)
        
        layout.addLayout(button_layout)
        
        # Annotation controls
        annotation_layout = QHBoxLayout()
        annotation_label = QLabel("Annotations:")
        annotation_label.setStyleSheet("font-weight: bold;")
        
        self.clear_markers_button = QPushButton("Clear Markers")
        self.clear_markers_button.setFocusPolicy(Qt.NoFocus)
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
        
        # Marker color picker button
        self.marker_color_button = QPushButton("🎨 Marker Color")
        self.marker_color_button.setFixedHeight(self.clear_markers_button.sizeHint().height())
        self.marker_color_button.setMaximumWidth(120)
        self.marker_color_button.setFocusPolicy(Qt.NoFocus)
        self.marker_color_button.setToolTip("Change annotation arrow color")
        self._update_marker_color_button()
        self.marker_color_button.clicked.connect(self._pick_marker_color)
        
        annotation_help = QLabel("Left-click: Add | Drag: Move | Scroll: Rotate | Shift+Scroll: Length | Right-click: Remove")
        annotation_help.setStyleSheet("color: #666666; font-size: 10px;")
        
        annotation_layout.addWidget(annotation_label)
        annotation_layout.addWidget(self.clear_markers_button)
        annotation_layout.addWidget(self.marker_color_button)
        annotation_layout.addWidget(annotation_help)
        annotation_layout.addStretch()
        layout.addLayout(annotation_layout)
        
        # Overlay controls
        overlay_layout = QHBoxLayout()
        self.overlay_checkbox = QCheckBox("Enable Overlay")
        self.overlay_checkbox.setStyleSheet("font-weight: bold;")
        self.overlay_checkbox.setEnabled(False)
        self.overlay_label = QLabel("No overlay loaded")
        self.overlay_label.setStyleSheet("color: #666666; font-size: 10px;")
        self.overlay_clear_button = QPushButton("✕")
        self.overlay_clear_button.setMaximumWidth(30)
        self.overlay_clear_button.setFocusPolicy(Qt.NoFocus)
        self.overlay_clear_button.setToolTip("Remove overlay")
        self.overlay_clear_button.setVisible(False)
        self.overlay_clear_button.clicked.connect(self._clear_overlay)
        overlay_layout.addWidget(self.overlay_checkbox)
        overlay_layout.addWidget(self.overlay_label)
        overlay_layout.addWidget(self.overlay_clear_button)
        overlay_layout.addStretch()
        layout.addLayout(overlay_layout)
        
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
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        # Space: Capture image
        if event.key() == Qt.Key_Space and self.capture_button.isEnabled() and not self.notes_input.hasFocus():
            self.capture_image()
            event.accept()
        # R: Toggle recording
        elif event.key() == Qt.Key_R and self.record_button.isEnabled() and not self.notes_input.hasFocus():
            self.toggle_recording()
            event.accept()
        # B: Scan barcode
        elif event.key() == Qt.Key_B and self.scan_button.isEnabled() and not self.notes_input.hasFocus():
            self.scan_barcode()
            event.accept()
        else:
            super().keyPressEvent(event)
    
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
                logger.debug("Stopping QR scanner...")
                self.qr_scanner.stop()
                self.qr_scanner = None
                logger.debug("QR scanner stopped")
            
            if self.current_camera:
                self.current_camera.close()
                self.current_camera = None
            
            if index >= 0 and index < len(self.available_cameras):
                self.current_camera = self.available_cameras[index]
                if self.current_camera.open():
                    # Apply settings (resolution + any user-saved config)
                    try:
                        from camera.camera_config_manager import CameraConfigManager
                        CameraConfigManager.initialize_camera_with_optimal_settings(
                            self.current_camera.capture, self.current_camera.name)
                    except Exception as e:
                        logger.warning(f"Could not apply camera settings: {e}")
                    
                    self.timer.start(30)  # 30ms refresh
                    self.capture_button.setEnabled(True)
                    self.record_button.setEnabled(True)
                    self.status_label.setText(f"Connected to {self.current_camera.name}")
                    
                    # Start QR scanner if available
                    if QR_SCANNER_AVAILABLE:
                        logger.debug("Starting barcode scanner...")
                        self.qr_scanner = QRScannerThread()
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
            # Close camera if it was opened but setup failed
            if self.current_camera and self.current_camera.is_open:
                self.current_camera.close()
                self.current_camera = None
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
        
        if self.audit:
            self.audit.log("barcode_scan", {"type": barcode_type, "data": barcode_data, "source": "camera"})
    
    def on_usb_barcode_scanned(self, barcode_data):
        """Handle barcode from USB HID scanner - same data path as camera scan."""
        scan_info = {
            'type': 'USB-HID',
            'data': barcode_data,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.barcode_scans.append(scan_info)
        
        # Capture current frame if camera is active
        if self.current_camera:
            frame = self.current_camera.capture_frame()
            if frame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"barcode_scan_{timestamp}.jpg"
                filepath = os.path.join(self.output_dir, filename)
                cv2.imwrite(filepath, frame)
                
                self.captured_images.append({
                    'path': filepath,
                    'camera': self.current_camera.name,
                    'notes': f"USB barcode scan: {barcode_data}",
                    'barcode_scans': [scan_info]
                })
        
        scan_count = len(self.barcode_scans)
        msg = QMessageBox(self)
        msg.setWindowTitle("USB Barcode Scanned")
        msg.setText(f"Barcode Data: {barcode_data}\n\nScan {scan_count} for this session")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
        
        self.status_label.setText(f"USB barcode scanned ({scan_count} total)")
        
        if self.audit:
            self.audit.log("barcode_scan", {"type": "USB-HID", "data": barcode_data, "source": "usb"})

    def open_review_dialog(self):
        """Open review captures dialog."""
        if not self.captured_images:
            QMessageBox.information(self, "No Captures", "No images or videos have been captured yet.")
            return
        
        dialog = ReviewCapturesDialog(self.captured_images, parent=self)
        dialog.exec_()
    
    def open_mask_editor(self):
        """Open overlay mask editor with choice of image source."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Create Overlay Mask")
        msg.setText("Choose an image source for the overlay mask editor:")
        msg.setIcon(QMessageBox.Question)
        
        capture_btn = msg.addButton("📷 Capture Current Frame", QMessageBox.ActionRole)
        browse_btn = msg.addButton("📂 Browse for Image...", QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Cancel)
        
        # Disable capture if no camera active
        if not self.current_camera:
            capture_btn.setEnabled(False)
            capture_btn.setToolTip("No camera is currently active")
        
        msg.exec_()
        clicked = msg.clickedButton()
        
        image_path = None
        if clicked == capture_btn:
            frame = self.current_camera.capture_frame()
            if frame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"mask_source_{timestamp}.png"
                image_path = os.path.join(self.output_dir, filename)
                cv2.imwrite(image_path, frame)
            else:
                QMessageBox.warning(self, "Capture Failed", "Could not capture a frame from the camera.")
                return
        elif clicked == browse_btn:
            # Start browsing from the captured_images output directory
            start_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     "output", "captured_images")
            image_path, _ = QFileDialog.getOpenFileName(
                self, "Select Image for Mask Editor", start_dir,
                "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp);;All Files (*)")
            if not image_path:
                return
        else:
            return
        
        dialog = MaskEditorDialog(image_path=image_path, parent=self)
        dialog.exec_()
        if dialog.saved_path:
            self._set_overlay(dialog.saved_path)

    def _set_overlay(self, path):
        """Set the active overlay image."""
        self.overlay_path = path
        self._overlay_cache = None
        self._overlay_cache_size = None
        self._overlay_cache_scaled = None
        self.overlay_checkbox.setEnabled(True)
        self.overlay_checkbox.setChecked(True)
        self.overlay_label.setText(os.path.basename(path))
        self.overlay_label.setStyleSheet("color: #9C27B0; font-size: 10px; font-weight: bold;")
        self.overlay_clear_button.setVisible(True)

    def _clear_overlay(self):
        """Remove the active overlay."""
        self.overlay_path = None
        self._overlay_cache = None
        self._overlay_cache_size = None
        self._overlay_cache_scaled = None
        self.overlay_checkbox.setChecked(False)
        self.overlay_checkbox.setEnabled(False)
        self.overlay_label.setText("No overlay loaded")
        self.overlay_label.setStyleSheet("color: #666666; font-size: 10px;")
        self.overlay_clear_button.setVisible(False)

    def _apply_overlay(self, frame):
        """Apply the active overlay onto a frame. Returns the blended frame."""
        if not self.overlay_path or not self.overlay_checkbox.isChecked():
            return frame
        try:
            # Load raw overlay once and cache it
            if self._overlay_cache is None:
                if not os.path.exists(self.overlay_path):
                    return frame
                img = cv2.imread(self.overlay_path, cv2.IMREAD_UNCHANGED)
                if img is None or img.shape[2] != 4:
                    return frame
                self._overlay_cache = img
                self._overlay_cache_size = None  # force re-scale

            h, w = frame.shape[:2]
            # Re-scale only when frame dimensions change
            if self._overlay_cache_size != (w, h):
                ref_scaled = cv2.resize(self._overlay_cache, (w, h), interpolation=cv2.INTER_LINEAR)
                alpha = ref_scaled[:, :, 3].astype(np.float32) / 255.0
                self._overlay_cache_scaled = (
                    ref_scaled[:, :, :3].astype(np.float32),
                    np.stack([alpha] * 3, axis=2),
                )
                self._overlay_cache_size = (w, h)

            overlay_bgr, alpha_3ch = self._overlay_cache_scaled
            blended = (overlay_bgr * alpha_3ch +
                       frame.astype(np.float32) * (1 - alpha_3ch)).astype(np.uint8)
            return blended
        except Exception:
            return frame

    def open_camera_settings(self):
        """Open camera settings dialog."""
        dialog = CameraSettingsDialog(self.available_cameras, parent=self)
        dialog.exec_()
    
    def update_frame(self):
        """Update camera preview."""
        if not self.current_camera:
            return
        
        try:
            frame = self.current_camera.capture_frame()
        except Exception as e:
            logger.error(f"Camera read error: {e}")
            frame = None
        
        if frame is not None:
            self._consecutive_frame_failures = 0
            
            # Feed frame to QR scanner (thread-safe)
            if self.qr_scanner:
                self.qr_scanner.update_frame(frame)
            
            # Apply overlay to display/recording frame
            display_frame = self._apply_overlay(frame)
            
            if self.is_recording and self.video_writer:
                # Draw markers on frame for video
                annotated_frame = display_frame.copy()
                if self.preview_label.markers:
                    annotated_frame = self._draw_markers_on_frame(annotated_frame, self.preview_label.markers, self._get_marker_bgr_color())
                self.video_writer.write(annotated_frame)
            
            # Convert to QImage for display
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Scale to fit preview
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.preview_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.preview_label.set_frame(scaled_pixmap)
        else:
            # Frame was None — camera may have disconnected
            self._consecutive_frame_failures = getattr(self, '_consecutive_frame_failures', 0) + 1
            if self._consecutive_frame_failures == 90:  # ~3 seconds at 30fps
                self.timer.stop()
                self.capture_button.setEnabled(False)
                self.record_button.setEnabled(False)
                result = QMessageBox.warning(
                    self, "Camera Not Responding",
                    f"Camera '{self.current_camera.name}' has stopped providing frames.\n\n"
                    "This may be caused by a disconnected cable or the camera being used by another application.\n\n"
                    "Would you like to try reconnecting?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if result == QMessageBox.Yes:
                    self._consecutive_frame_failures = 0
                    cam_index = self.camera_combo.currentIndex()
                    self.on_camera_changed(cam_index)
                else:
                    self.preview_label.setText("⚠️ Camera disconnected")
    
    def capture_image(self):
        """Capture and save a single image with annotations."""
        if not self.current_camera:
            return
        
        frame = self.current_camera.capture_frame()
        if frame is not None:
            # Apply overlay before review
            frame = self._apply_overlay(frame)
            
            # Carry over any markers already placed on the live preview
            existing_markers = self.preview_label.get_markers_data()
            existing_notes = self.notes_input.text().strip()

            # Open review dialog for annotation and notes
            dlg = CaptureReviewDialog(
                frame,
                marker_color=self.preview_label.marker_color,
                existing_markers=existing_markers,
                existing_notes=existing_notes,
                parent=self
            )
            if dlg.exec_() != dlg.Accepted:
                return  # Discarded

            markers, notes = dlg.get_results()

            # Draw markers on the frame if any exist
            if markers:
                frame = self._draw_markers_on_frame(frame, markers, self._get_marker_bgr_color())
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            serial_prefix = self.serial_number if self.serial_number else "unknown"
            filename = f"{serial_prefix}_{timestamp}.jpg"
            filepath = os.path.join(self.output_dir, filename)
            
            cv2.imwrite(filepath, frame)
            
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
            
            # Audit trail
            if self.audit:
                self.audit.log("image_capture", {
                    "filename": filename,
                    "markers": [m.get("label", "") for m in markers] if markers else [],
                    "has_notes": bool(notes),
                })
            
            # Clear notes and markers for next image
            self.notes_input.clear()
            self.preview_label.clear_markers()
            
            self.status_label.setText(f"Image saved: {filename} (Total: {len(self.captured_images)})")
    
    def _get_marker_bgr_color(self):
        """Get the current marker color as a BGR tuple for OpenCV."""
        c = self.preview_label.marker_color
        return (c.blue(), c.green(), c.red())

    def _update_marker_color_button(self):
        """Update the color picker button to show the current marker color."""
        c = self.preview_label.marker_color
        self.marker_color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {c.name()};
                border: 2px solid #888;
                border-radius: 3px;
                padding: 5px 15px;
            }}
            QPushButton:hover {{
                border-color: #444;
            }}
        """)

    def _pick_marker_color(self):
        """Open color picker for annotation arrows."""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.preview_label.marker_color, self, "Annotation Arrow Color")
        if color.isValid():
            self.preview_label.marker_color = color
            self._update_marker_color_button()
            self.preview_label.update()

    def _draw_markers_on_frame(self, frame, markers, color=(0, 0, 255)):
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
            cv2.arrowedLine(frame, (x, y), (end_x, end_y), color, 2, tipLength=0.3)
            
            # Label circle at arrow tip
            cv2.circle(frame, (end_x, end_y), 12, (255, 255, 255), -1)
            cv2.circle(frame, (end_x, end_y), 12, color, 2)
            
            # Label text
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(label, font, 0.5, 2)[0]
            text_x = end_x - text_size[0] // 2
            text_y = end_y + text_size[1] // 2
            cv2.putText(frame, label, (text_x, text_y), font, 0.5, color, 2)
        
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
            logger.error(f"Failed to save metadata: {e}")
    
    def toggle_recording(self):
        """Start or stop video recording."""
        if not self.is_recording:
            # Start recording
            try:
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
                self.record_button.setText("⏹ Stop Recording (R)")
                self.capture_button.setEnabled(False)
                self.status_label.setText(f"Recording: {filename}")
                
                if self.audit:
                    self.audit.log("recording_start", {"filename": filename})
            except Exception as e:
                logger.error(f"Failed to start recording: {e}", exc_info=True)
                if self.video_writer:
                    self.video_writer.release()
                    self.video_writer = None
                self.is_recording = False
                self.status_label.setText(f"Recording error: {str(e)}")
        else:
            # Stop recording
            self.is_recording = False
            try:
                if self.video_writer:
                    self.video_writer.release()
                    self.video_writer = None
            except Exception as e:
                logger.error(f"Error releasing video writer: {e}", exc_info=True)
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
            
            self.record_button.setText("🔴 Start Recording (R)")
            self.capture_button.setEnabled(True)
            self.status_label.setText(f"Recording stopped (Total: {len(self.captured_images)})")
            
            if self.audit:
                self.audit.log("recording_stop", {"filename": os.path.basename(self.current_video_path)})
    
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
                    barcode_scans=self.barcode_scans if self.barcode_scans else None,
                    output_dir=self._reports_dir
                )
                self.report_generated = True
                self.status_label.setText(f"✓ Reports saved")
                
                if self.audit:
                    self.audit.log("report_generated", {
                        "pdf": os.path.basename(pdf_path) if pdf_path else None,
                        "docx": os.path.basename(docx_path) if docx_path else None,
                        "image_count": len(self.captured_images),
                    })
                
                # Show enhanced report dialog
                self.show_report_dialog(pdf_path, docx_path, len(self.captured_images))
            except Exception as e:
                logger.error(f"Report generation error", exc_info=True)
                QMessageBox.warning(
                    self,
                    "Report Error",
                    f"Failed to generate report:\n{str(e)}\n\nCheck logs for details."
                )
        
        self.cleanup_resources()
        self.back_requested.emit()
    
    def show_report_dialog(self, pdf_path, docx_path, image_count):
        """Show enhanced report dialog with view options."""
        from PyQt5.QtWidgets import QDialog, QRadioButton, QButtonGroup
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Reports Generated")
        dialog.setModal(True)
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Success message
        success_label = QLabel("✓ PDF and DOCX reports generated successfully!")
        success_label.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
        layout.addWidget(success_label)
        
        # Warn if reports were saved to fallback location
        if self._prefs.is_reports_dir_fallback():
            fallback_label = QLabel(
                f"⚠️ Custom reports folder is unavailable. "
                f"Reports saved locally instead."
            )
            fallback_label.setWordWrap(True)
            fallback_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #E65100; padding: 4px;")
            layout.addWidget(fallback_label)
        
        layout.addSpacing(10)
        
        # File paths
        info_label = QLabel(
            f"PDF: {pdf_path}\n\n"
            f"DOCX: {docx_path}\n\n"
            f"Images included: {image_count}"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(info_label)
        
        layout.addSpacing(15)
        
        # Format selection
        format_label = QLabel("Select format to view:")
        format_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(format_label)
        
        format_group = QButtonGroup(dialog)
        pdf_radio = QRadioButton("PDF")
        pdf_radio.setChecked(True)
        docx_radio = QRadioButton("DOCX")
        
        format_group.addButton(pdf_radio, 1)
        format_group.addButton(docx_radio, 2)
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(pdf_radio)
        format_layout.addWidget(docx_radio)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        layout.addSpacing(15)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        view_button = QPushButton("View Report")
        view_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
        """)
        
        def open_report():
            file_path = pdf_path if pdf_radio.isChecked() else docx_path
            try:
                if platform.system() == "Windows":
                    os.startfile(file_path)
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", file_path])
                else:
                    subprocess.Popen(["xdg-open", file_path])
                dialog.accept()
            except Exception as e:
                QMessageBox.warning(dialog, "Error", f"Could not open file:\n{str(e)}")
        
        view_button.clicked.connect(open_report)
        button_layout.addWidget(view_button)
        
        menu_button = QPushButton("Return to Menu")
        menu_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        menu_button.clicked.connect(dialog.accept)
        button_layout.addWidget(menu_button)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def cleanup_resources(self):
        """Clean up resources before closing."""
        # Stop timer immediately
        try:
            if self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass
        
        # Stop barcode check timer
        try:
            if self.barcode_check_timer and self.barcode_check_timer.isActive():
                self.barcode_check_timer.stop()
        except Exception:
            pass
        
        # Stop recording if active
        try:
            if self.is_recording and self.video_writer:
                self.video_writer.release()
        except Exception:
            logger.warning("Error releasing video writer during cleanup", exc_info=True)
        finally:
            self.video_writer = None
            self.is_recording = False
        
        # Stop QR scanner without waiting
        try:
            if self.qr_scanner:
                self.qr_scanner.stop()
        except Exception:
            logger.warning("Error stopping QR scanner during cleanup", exc_info=True)
        finally:
            self.qr_scanner = None
        
        # Close camera
        try:
            if self.current_camera:
                self.current_camera.close()
        except Exception:
            logger.warning("Error closing camera during cleanup", exc_info=True)
        finally:
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
                
                # Show enhanced report dialog
                self.show_report_dialog(pdf_path, docx_path, len(self.captured_images))
            except Exception as e:
                # Show error but don't block exit
                QMessageBox.warning(
                    self,
                    "Report Error",
                    f"Failed to generate report:\n{str(e)}"
                )
                logger.error(f"Report generation error", exc_info=True)
        
        self.cleanup_resources()
        event.accept()
