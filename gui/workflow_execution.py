"""Workflow execution screen for guided QC and maintenance procedures."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QMessageBox, QLineEdit, QSplitter, QComboBox, QDialog, QSizePolicy, QCheckBox, QRadioButton, QButtonGroup, QSlider)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QColor, QPen
import cv2
import os
import json
import numpy as np
import tempfile
from datetime import datetime
from camera import CameraManager
from reports import generate_reports
from gui.annotatable_preview import AnnotatablePreview
from gui.review_captures_dialog import ReviewCapturesDialog
from gui.camera_settings_dialog import CameraSettingsDialog
from gui.video_decoder import VideoDecoderThread
from gui.checkbox_widgets import InteractiveReferenceImage, CombinedReferenceImage
from gui.comparison_dialog import show_reference_fullsize
from gui.overlay_renderer import (render_overlay_on_frame, draw_markers_on_frame,
                                  draw_reference_annotations)
from gui.overlay_comparison_dialog import show_overlay_comparison
from gui.video_comparison_dialog import show_video_comparison
from gui.workflow_progress import (save_workflow_progress, load_workflow_progress,
                                   clear_workflow_progress)
from gui.workflow_report import (generate_workflow_report, show_report_dialog,
                                 generate_checkbox_image)
from logger_config import get_logger

logger = get_logger(__name__)

# Optional QR scanner support
try:
    from qr_scanner import QRScannerThread
    QR_SCANNER_AVAILABLE = True
except ImportError:
    QR_SCANNER_AVAILABLE = False
    logger.warning("QR scanner not available")
    QRScannerThread = None


class WorkflowExecutionScreen(QWidget):
    """Execute a workflow step-by-step with camera integration."""
    
    back_requested = pyqtSignal()
    
    def __init__(self, workflow_path, serial_number, technician, description, cached_cameras=None):
        super().__init__()
        self.workflow_path = workflow_path
        self.serial_number = serial_number
        self.technician = technician
        self.description = description
        self.current_step = 0
        self.max_step_reached = 0
        self.workflow = None
        self.current_camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.qr_scanner = None
        self.barcode_check_timer = None
        self.captured_images = []  # All images from workflow
        self.step_images = []  # Images for current step
        self.all_barcode_scans = []  # All barcode scans from workflow
        self.step_barcode_scans = []  # Barcode scans for current step
        self.step_results = {}  # Track pass/fail for each step: {step_index: bool}
        self.step_checkbox_states = {}  # Track checkbox states: {step_index: [{'x', 'y', 'checked'}]}
        
        # Video recording state
        self.is_recording = False
        self.video_writer = None
        self.current_video_path = None
        self.recorded_videos = []  # List of recorded video paths
        
        # Overlay transform state (persistent across views)
        self.overlay_scale = 100
        self.overlay_x_offset = 0
        self.overlay_y_offset = 0
        self.overlay_rotation = 0
        self.overlay_transparency = 100  # Default to 100% for overlays
        
        # Cached transformed overlay to avoid recomputing every frame
        self._overlay_cache = None  # The transformed BGRA canvas
        self._overlay_cache_params = None  # (path, scale, x, y, rot, w, h)
        
        # Use cached cameras if provided, otherwise discover
        self.available_cameras = cached_cameras if cached_cameras is not None else []
        self.recording_start_time = None
        
        # Setup output directory - sanitize serial number for filesystem
        output_serial = self._sanitize_filename(serial_number) if serial_number else "unknown"
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "output", "captured_images", output_serial)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.load_workflow()
        self.init_ui()
        
        # Only discover cameras if not already cached
        if not self.available_cameras:
            self.discover_cameras()
        else:
            logger.info(f"Using {len(self.available_cameras)} cached camera(s)")
            self.camera_combo.clear()
            for cam in self.available_cameras:
                self.camera_combo.addItem(cam.name)
        
        self.show_current_step()
        self.update_breadcrumb()

        # Defer progress loading so signals are connected before any dialogs/navigation
        QTimer.singleShot(0, self._deferred_load_progress)

        # Set focus to this widget so keyboard shortcuts work immediately
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Stop recording if active
        if self.is_recording and self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            logger.info("Video recording stopped due to window close")
        
        # Stop timer
        if self.timer.isActive():
            self.timer.stop()
        
        # Close camera
        if self.current_camera:
            self.current_camera.close()
        
        event.accept()
    
    def _sanitize_filename(self, filename):
        """Remove invalid characters from filename."""
        # Windows invalid characters: < > : " / \ | ? *
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # Also remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        return filename if filename else "unknown"
    
    def load_workflow(self):
        """Load workflow from JSON file."""
        try:
            logger.info(f"Loading workflow from: {self.workflow_path}")
            
            if not os.path.exists(self.workflow_path):
                raise FileNotFoundError(f"Workflow file not found: {self.workflow_path}")
            
            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                self.workflow = json.load(f)
            
            # Validate workflow structure
            if not isinstance(self.workflow, dict):
                raise ValueError("Workflow file must contain a JSON object")
            
            if 'steps' not in self.workflow:
                raise ValueError("Workflow must contain 'steps' array")
            
            if not isinstance(self.workflow['steps'], list):
                raise ValueError("Workflow 'steps' must be an array")
            
            logger.info(f"Workflow loaded successfully: {self.workflow.get('name', 'Unnamed')} "
                       f"with {len(self.workflow['steps'])} steps")
            
        except json.JSONDecodeError as e:
            logger.error(f"Workflow file is not valid JSON: {e}")
            QMessageBox.critical(self, "Workflow Error", 
                               f"Workflow file is corrupted or invalid:\n{str(e)}\n\n"
                               "Please check the workflow file format.")
            self.workflow = {"name": "Error", "steps": []}
        except Exception as e:
            logger.error(f"Failed to load workflow: {e}", exc_info=True)
            QMessageBox.critical(self, "Workflow Error", 
                               f"Failed to load workflow:\n{str(e)}")
            self.workflow = {"name": "Error", "steps": []}
    
    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Compact Header
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            background-color: #77C25E;
            border-radius: 3px;
        """)
        header_widget.setMaximumHeight(60)  # Limit header height
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Left side: Title and step info
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title = QLabel(self.workflow.get('name', 'Workflow'))
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        title_layout.addWidget(title)
        
        self.step_label = QLabel()
        self.step_label.setFont(QFont("Arial", 10))
        self.step_label.setStyleSheet("color: white; background: transparent;")
        title_layout.addWidget(self.step_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Right side: Back button
        self.back_button = QPushButton("← Back to Menu")
        self.back_button.setFocusPolicy(Qt.NoFocus)
        self.back_button.setStyleSheet("""
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
        self.back_button.clicked.connect(self.on_back_clicked)
        header_layout.addWidget(self.back_button)
        
        main_layout.addWidget(header_widget)
        
        # Step breadcrumb navigation
        self.breadcrumb_widget = QWidget()
        self.breadcrumb_widget.setStyleSheet("background-color: #F5F5F5; border-radius: 3px;")
        self.breadcrumb_widget.setMaximumHeight(40)
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb_layout.setContentsMargins(10, 5, 10, 5)
        self.breadcrumb_layout.setSpacing(5)
        main_layout.addWidget(self.breadcrumb_widget)
        
        # Main content area - split between instructions and camera
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Instructions and reference
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        inst_label = QLabel("Instructions:")
        inst_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        left_layout.addWidget(inst_label)
        
        self.instructions_text = QTextEdit()
        self.instructions_text.setReadOnly(True)
        left_layout.addWidget(self.instructions_text, 1)
        
        # Reference image header with button
        ref_header_layout = QHBoxLayout()
        ref_label = QLabel("Reference Image:")
        ref_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        ref_header_layout.addWidget(ref_label)
        ref_header_layout.addStretch()
        
        # Compare & Overlay button
        self.compare_button = QPushButton("🔍 Compare & Overlay")
        self.compare_button.setFocusPolicy(Qt.NoFocus)
        self.compare_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.compare_button.clicked.connect(self.show_comparison)
        self.compare_button.setEnabled(False)
        ref_header_layout.addWidget(self.compare_button)
        
        ref_header_layout.addStretch()
        
        left_layout.addLayout(ref_header_layout)
        
        self.reference_image = InteractiveReferenceImage()
        self.reference_image.setMinimumSize(400, 400)  # Increased from 300x200
        self.reference_image.setStyleSheet("border: 2px solid #CCCCCC;")
        self.reference_image.checkboxes_changed.connect(self.on_checkboxes_changed)
        self.reference_image_path = None  # Store current reference image path
        self.reference_checkboxes = []  # Store current checkboxes
        left_layout.addWidget(self.reference_image)
        
        # Reference video player (hidden by default)
        self.ref_video_widget = QWidget()
        ref_video_layout = QVBoxLayout(self.ref_video_widget)
        ref_video_layout.setContentsMargins(0, 0, 0, 0)
        ref_video_layout.setSpacing(3)
        
        self.ref_video_display = QLabel()
        self.ref_video_display.setMinimumSize(200, 200)
        self.ref_video_display.setStyleSheet("border: 2px solid #FF9800; background-color: #2b2b2b;")
        self.ref_video_display.setAlignment(Qt.AlignCenter)
        ref_video_layout.addWidget(self.ref_video_display, 1)
        
        # Video controls
        video_ctrl_layout = QHBoxLayout()
        self.ref_video_play_btn = QPushButton("▶ Play")
        self.ref_video_play_btn.setMaximumWidth(80)
        self.ref_video_play_btn.setStyleSheet("""
            QPushButton { background-color: #FF9800; color: white; border: none;
                border-radius: 3px; font-weight: bold; padding: 4px 8px; }
            QPushButton:hover { background-color: #F57C00; }
        """)
        self.ref_video_play_btn.clicked.connect(self._toggle_ref_video)
        video_ctrl_layout.addWidget(self.ref_video_play_btn)
        
        self.ref_video_restart_btn = QPushButton("⏮ Restart")
        self.ref_video_restart_btn.setMaximumWidth(80)
        self.ref_video_restart_btn.setStyleSheet("""
            QPushButton { background-color: #666; color: white; border: none;
                border-radius: 3px; font-weight: bold; padding: 4px 8px; }
            QPushButton:hover { background-color: #555; }
        """)
        self.ref_video_restart_btn.clicked.connect(self._restart_ref_video)
        video_ctrl_layout.addWidget(self.ref_video_restart_btn)
        
        self.ref_video_slider = QSlider(Qt.Horizontal)
        self.ref_video_slider.setMinimum(0)
        self.ref_video_slider.setMaximum(1000)
        self.ref_video_slider.sliderPressed.connect(self._ref_video_slider_pressed)
        self.ref_video_slider.sliderReleased.connect(self._ref_video_slider_released)
        self.ref_video_slider.sliderMoved.connect(self._ref_video_slider_moved)
        video_ctrl_layout.addWidget(self.ref_video_slider)
        
        self.ref_video_time_label = QLabel("0:00 / 0:00")
        self.ref_video_time_label.setMinimumWidth(90)
        video_ctrl_layout.addWidget(self.ref_video_time_label)
        
        ref_video_layout.addLayout(video_ctrl_layout)
        self.ref_video_widget.setVisible(False)
        left_layout.addWidget(self.ref_video_widget, 3)
        
        # Reference video state
        self.ref_video_path = None
        self._ref_video_thread = None
        self._ref_video_playing = False
        self._ref_video_slider_dragging = False
        
        splitter.addWidget(left_widget)
        
        # Right side - Camera view
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Camera selection with Review Captures button
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Camera:")
        camera_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        camera_label.setMinimumWidth(80)
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(250)
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo)
        
        # Camera settings button
        self.camera_settings_button = QPushButton("⚙️ Settings")
        self.camera_settings_button.setMaximumWidth(100)
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
        
        # Review captures button (right-aligned)
        self.review_button = QPushButton("📋 Review Captures")
        self.review_button.setMaximumWidth(180)
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
        camera_layout.addWidget(self.review_button)
        
        right_layout.addLayout(camera_layout)
        
        # Camera preview - larger and expandable
        preview_container = QWidget()
        preview_container_layout = QVBoxLayout(preview_container)
        preview_container_layout.setContentsMargins(0, 0, 0, 0)
        preview_container_layout.setSpacing(0)
        
        self.preview_label = AnnotatablePreview()
        self.preview_label.setStyleSheet("border: 2px solid #77C25E; background-color: #2b2b2b;")
        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        preview_container_layout.addWidget(self.preview_label, 1)
        
        # Hide overlay checkbox (only visible when PNG overlay is present)
        hide_overlay_layout = QHBoxLayout()
        
        self.hide_overlay_checkbox = QCheckBox("Hide Overlay Image")
        self.hide_overlay_checkbox.setStyleSheet("""
            QCheckBox {
                background-color: rgba(33, 150, 243, 180);
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.hide_overlay_checkbox.setVisible(False)
        hide_overlay_layout.addWidget(self.hide_overlay_checkbox)
        
        # Warning label (only visible when checkbox is checked)
        self.overlay_hidden_warning = QLabel("⚠️ Overlay Hidden - Not captured in images/video")
        self.overlay_hidden_warning.setStyleSheet("""
            QLabel {
                background-color: rgba(220, 53, 69, 200);
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 3px;
            }
        """)
        self.overlay_hidden_warning.setVisible(False)
        hide_overlay_layout.addWidget(self.overlay_hidden_warning)
        
        hide_overlay_layout.addStretch()
        
        hide_overlay_widget = QWidget()
        hide_overlay_widget.setLayout(hide_overlay_layout)
        preview_container_layout.addWidget(hide_overlay_widget)
        
        # Connect checkbox to show/hide warning
        self.hide_overlay_checkbox.toggled.connect(self.overlay_hidden_warning.setVisible)
        
        # Recording indicator overlay
        self.recording_indicator = QLabel("🔴 REC 00:00")
        self.recording_indicator.setStyleSheet("""
            QLabel {
                background-color: rgba(220, 53, 69, 200);
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 5px 10px;
                border-radius: 3px;
            }
        """)
        self.recording_indicator.setVisible(False)
        self.recording_indicator.setAlignment(Qt.AlignCenter)
        preview_container_layout.addWidget(self.recording_indicator)
        
        right_layout.addWidget(preview_container, 1)  # Stretch factor 1 to take available space
        
        # Annotation controls
        annotation_layout = QHBoxLayout()
        self.clear_markers_button = QPushButton("Clear Markers")
        self.clear_markers_button.setFocusPolicy(Qt.NoFocus)
        self.clear_markers_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #FF5252;
            }
        """)
        self.clear_markers_button.clicked.connect(self.preview_label.clear_markers)
        annotation_layout.addWidget(self.clear_markers_button)
        
        # Marker color picker button
        self.marker_color_button = QPushButton("🎨 Marker Color")
        self.marker_color_button.setFocusPolicy(Qt.NoFocus)
        self.marker_color_button.setFixedHeight(self.clear_markers_button.sizeHint().height())
        self.marker_color_button.setMaximumWidth(120)
        self.marker_color_button.setToolTip("Change annotation arrow color")
        self._update_marker_color_button()
        self.marker_color_button.clicked.connect(self._pick_marker_color)
        annotation_layout.addWidget(self.marker_color_button)
        
        annotation_help = QLabel("Click: Add | Drag: Move | Scroll: Rotate | Right-click: Remove")
        annotation_help.setStyleSheet("color: #888888; font-size: 10px;")
        annotation_layout.addWidget(annotation_help)
        annotation_layout.addStretch()
        right_layout.addLayout(annotation_layout)
        
        # Notes input
        notes_layout = QHBoxLayout()
        notes_label = QLabel("Notes:")
        notes_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Add notes for this step...")
        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(self.notes_input)
        right_layout.addLayout(notes_layout)
        
        # Capture and record buttons in a row
        capture_layout = QHBoxLayout()
        
        # Capture button
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.setMinimumHeight(40)
        self.capture_button.setToolTip("Capture an image from the camera (Space)")
        self.capture_button.clicked.connect(self.capture_image)
        self.capture_button.setEnabled(False)
        capture_layout.addWidget(self.capture_button)
        
        # Scan barcode button
        self.scan_button = QPushButton("Scan Barcode/QR")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setMaximumWidth(150)
        self.scan_button.setToolTip("Scan a barcode or QR code (B)")
        self.scan_button.clicked.connect(self.scan_barcode)
        self.scan_button.setEnabled(False)
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
        capture_layout.addWidget(self.scan_button)
        
        # Record button
        self.record_button = QPushButton("🔴 Start Recording")
        self.record_button.setMinimumHeight(40)
        self.record_button.setToolTip("Start/stop video recording (R)")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setEnabled(False)
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
        capture_layout.addWidget(self.record_button)
        
        right_layout.addLayout(capture_layout)
        
        # Pass/Fail buttons (only shown when step requires it)
        self.pass_fail_widget = QWidget()
        pass_fail_layout = QHBoxLayout(self.pass_fail_widget)
        pass_fail_layout.setContentsMargins(0, 0, 0, 0)
        
        pass_fail_label = QLabel("Mark Step Result:")
        pass_fail_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        pass_fail_layout.addWidget(pass_fail_label)
        
        self.pass_button = QPushButton("✓ Pass")
        self.pass_button.setFocusPolicy(Qt.NoFocus)
        self.pass_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        self.pass_button.clicked.connect(lambda: self.mark_step_result(True))
        pass_fail_layout.addWidget(self.pass_button)
        
        self.fail_button = QPushButton("✗ Fail")
        self.fail_button.setFocusPolicy(Qt.NoFocus)
        self.fail_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.fail_button.clicked.connect(lambda: self.mark_step_result(False))
        pass_fail_layout.addWidget(self.fail_button)
        
        pass_fail_layout.addStretch()
        self.pass_fail_widget.setVisible(False)  # Hidden by default
        right_layout.addWidget(self.pass_fail_widget)
        
        self.step_status = QLabel()
        self.step_status.setStyleSheet("color: #888888; font-size: 11px;")
        right_layout.addWidget(self.step_status)
        
        # Auto-save status indicator
        self.autosave_label = QLabel()
        self.autosave_label.setStyleSheet("color: #4CAF50; font-size: 10px; font-style: italic;")
        self.autosave_label.setAlignment(Qt.AlignRight)
        right_layout.addWidget(self.autosave_label)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("← Previous Step")
        self.prev_button.setMinimumHeight(50)
        self.prev_button.setFocusPolicy(Qt.NoFocus)
        self.prev_button.setToolTip("Go to the previous step")
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #666666;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)
        self.prev_button.clicked.connect(self.previous_step)
        nav_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("Next Step →")
        self.next_button.setMinimumHeight(50)
        self.next_button.setFocusPolicy(Qt.NoFocus)
        self.next_button.setToolTip("Advance to the next step (Enter)")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)
        self.next_button.clicked.connect(self.next_step)
        nav_layout.addWidget(self.next_button)
        
        self.finish_button = QPushButton("Finish Workflow")
        self.finish_button.setMinimumHeight(50)
        self.finish_button.setFocusPolicy(Qt.NoFocus)
        self.finish_button.setToolTip("Complete the workflow and generate report (Enter)")
        self.finish_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        self.finish_button.clicked.connect(self.finish_workflow)
        self.finish_button.setVisible(False)
        nav_layout.addWidget(self.finish_button)
        
        main_layout.addLayout(nav_layout)
        
        self.setLayout(main_layout)
    
    def discover_cameras(self):
        """Discover available cameras."""
        try:
            logger.info("Discovering cameras...")
            cameras = CameraManager.discover_cameras()
            for cam in cameras:
                cam.close()
            
            self.camera_combo.clear()
            self.available_cameras = cameras
            
            for cam in cameras:
                self.camera_combo.addItem(cam.name)
            
            logger.info(f"Found {len(cameras)} camera(s)")
        except Exception as e:
            logger.error(f"Camera discovery error: {e}", exc_info=True)
            self.available_cameras = []
            QMessageBox.warning(self, "Camera Discovery Error",
                              f"Failed to discover cameras:\n{str(e)}\n\nPlease check camera connections.")
    
    def on_camera_changed(self, index):
        """Handle camera selection change."""
        try:
            self.timer.stop()
            
            if self.qr_scanner:
                self.qr_scanner.stop()
                self.qr_scanner = None
            
            if self.current_camera:
                self.current_camera.close()
                self.current_camera = None
            
            if index >= 0 and index < len(self.available_cameras):
                self.current_camera = self.available_cameras[index]
                logger.info(f"Switching to camera: {self.current_camera.name}")
                
                if self.current_camera.open():
                    # Apply settings (resolution + any user-saved config)
                    try:
                        from camera.camera_config_manager import CameraConfigManager
                        CameraConfigManager.initialize_camera_with_optimal_settings(
                            self.current_camera.capture, self.current_camera.name)
                    except Exception as e:
                        logger.warning(f"Could not apply camera settings: {e}")
                    
                    self.timer.start(30)
                    self.capture_button.setEnabled(True)
                    self.record_button.setEnabled(True)
                    logger.info("Camera opened successfully")
                    
                    # Start barcode scanner if available
                    if QR_SCANNER_AVAILABLE:
                        logger.info("Starting barcode scanner...")
                        self.qr_scanner = QRScannerThread()
                        self.qr_scanner.barcode_detected.connect(self.on_barcode_detected)
                        self.qr_scanner.start()
                        # Start timer to check barcode availability
                        self.barcode_check_timer = QTimer()
                        self.barcode_check_timer.timeout.connect(self.update_scan_button_state)
                        self.barcode_check_timer.start(100)
                else:
                    raise Exception(f"Failed to open camera: {self.current_camera.name}")
        except Exception as e:
            logger.error(f"Camera error: {e}", exc_info=True)
            QMessageBox.warning(self, "Camera Error",
                              f"Failed to open camera:\n{str(e)}\n\nTry selecting a different camera.")
            self.capture_button.setEnabled(False)
    
    def update_frame(self):
        """Update camera preview."""
        if not self.current_camera:
            return
        
        try:
            frame = self.current_camera.capture_frame()
            if frame is not None:
                self._consecutive_frame_failures = 0
                
                # Feed frame to QR scanner (thread-safe)
                if self.qr_scanner:
                    self.qr_scanner.update_frame(frame)
                
                # Check if current step has PNG overlay with alpha
                has_overlay = False
                has_alpha = False
                if self.workflow and self.reference_image_path and os.path.exists(self.reference_image_path):
                    ref_test = cv2.imread(self.reference_image_path, cv2.IMREAD_UNCHANGED)
                    has_alpha = ref_test is not None and len(ref_test.shape) == 3 and ref_test.shape[2] == 4
                    # Only apply overlay if checkbox is not checked (i.e., not hidden)
                    has_overlay = has_alpha and not self.hide_overlay_checkbox.isChecked()
                
                # Apply overlay if present and not hidden
                display_frame = frame.copy()
                if has_overlay:
                    display_frame = self._render_overlay_on_frame(display_frame, self.reference_image_path, has_alpha)
                
                # If recording, write frame with overlay and annotations to video
                if self.is_recording and self.video_writer:
                    annotated_frame = display_frame.copy()
                    if self.preview_label.markers:
                        annotated_frame = self._draw_markers_on_frame(annotated_frame, self.preview_label.markers, self._get_marker_bgr_color())
                    self.video_writer.write(annotated_frame)
                    
                    # Update recording timer
                    if self.recording_start_time:
                        elapsed = (datetime.now() - self.recording_start_time).total_seconds()
                        minutes = int(elapsed // 60)
                        seconds = int(elapsed % 60)
                        self.recording_indicator.setText(f"🔴 REC {minutes:02d}:{seconds:02d}")
                
                # Update preview
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                    self.preview_label.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.set_frame(scaled_pixmap)
            else:
                # Frame was None — camera may have disconnected
                self._consecutive_frame_failures = getattr(self, '_consecutive_frame_failures', 0) + 1
                if self._consecutive_frame_failures == 90:  # ~3 seconds at 30fps
                    logger.warning(f"Camera not responding after {self._consecutive_frame_failures} frames")
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
        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            # Don't show message box here as it would spam during continuous capture
            # Just log the error and continue
    
    def toggle_recording(self):
        """Start or stop video recording."""
        if not self.current_camera:
            return
        
        try:
            if not self.is_recording:
                # Start recording
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_filename = f"video_{timestamp}.mp4"
                self.current_video_path = os.path.join(self.output_dir, video_filename)
                
                # Get frame dimensions
                frame = self.current_camera.capture_frame()
                if frame is None:
                    raise Exception("Cannot start recording: no frame available")
                
                h, w = frame.shape[:2]
                
                # Initialize video writer (using H.264 codec for MP4, 30 fps)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.video_writer = cv2.VideoWriter(self.current_video_path, fourcc, 30.0, (w, h))
                
                if not self.video_writer.isOpened():
                    raise Exception("Failed to initialize video writer")
                
                self.is_recording = True
                self.recording_start_time = datetime.now()
                self.recording_indicator.setVisible(True)
                self.record_button.setText("⏹ Stop Recording")
                self.record_button.setStyleSheet("""
                    QPushButton {
                        background-color: #28A745;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #218838;
                    }
                """)
                logger.info(f"Started recording video: {self.current_video_path}")
                
            else:
                # Stop recording
                if self.video_writer:
                    self.video_writer.release()
                    self.video_writer = None
                
                self.is_recording = False
                self.recording_indicator.setVisible(False)
                self.record_button.setText("🔴 Start Recording")
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
                
                # Add to recorded videos list
                if self.current_video_path and os.path.exists(self.current_video_path):
                    self.recorded_videos.append(self.current_video_path)
                    logger.info(f"Stopped recording. Video saved: {self.current_video_path}")
                    QMessageBox.information(self, "Recording Stopped", 
                                          f"Video saved:\n{os.path.basename(self.current_video_path)}")
                
                self.current_video_path = None
                
        except Exception as e:
            logger.error(f"Video recording error: {e}", exc_info=True)
            QMessageBox.warning(self, "Recording Error",
                              f"Failed to record video:\n{str(e)}")
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
    
    def show_current_step(self):
        """Display the current step information."""
        if not self.workflow or 'steps' not in self.workflow:
            return
        
        steps = self.workflow['steps']
        if self.current_step >= len(steps):
            return
        
        step = steps[self.current_step]
        
        # Update breadcrumb
        self.update_breadcrumb()
        
        # Update header
        self.step_label.setText(f"Step {self.current_step + 1} of {len(steps)}: {step.get('title', 'Untitled')}")
        
        # Update instructions
        self.instructions_text.setText(step.get('instructions', 'No instructions provided.'))
        
        # Update reference image
        ref_image_path = step.get('reference_image', '')
        ref_video_path = step.get('reference_video', '')
        checkbox_data = step.get('inspection_checkboxes', [])
        
        # Stop any playing reference video from previous step
        self._close_ref_video()
        
        # Determine if this step has a reference video
        has_ref_video = bool(ref_video_path and os.path.exists(ref_video_path))
        self.ref_video_widget.setVisible(has_ref_video)
        self.reference_image.setVisible(not has_ref_video)
        
        if has_ref_video:
            self.ref_video_path = ref_video_path
            self._open_ref_video(ref_video_path)
        
        # Only load if path exists and is not empty
        if ref_image_path and os.path.exists(ref_image_path):
            self.reference_image_path = ref_image_path
            self.reference_image.set_image_and_checkboxes(ref_image_path, checkbox_data)
            self.compare_button.setEnabled(True)
            
            # Update button label based on image type
            ref_test = cv2.imread(ref_image_path, cv2.IMREAD_UNCHANGED)
            has_alpha = ref_test is not None and len(ref_test.shape) == 3 and ref_test.shape[2] == 4
            if has_alpha:
                self.compare_button.setText("⚙️ Overlay Settings/Zoom View")
                self.hide_overlay_checkbox.setVisible(True)
                self.hide_overlay_checkbox.setChecked(False)
                # Load persisted overlay transforms for this step
                saved = step.get('overlay_transforms', {})
                self.overlay_scale = saved.get('scale', 100)
                self.overlay_x_offset = saved.get('x_offset', 0)
                self.overlay_y_offset = saved.get('y_offset', 0)
                self.overlay_rotation = saved.get('rotation', 0)
                self.overlay_transparency = saved.get('transparency', 100)
                self._overlay_cache_params = None  # Invalidate cache
            else:
                self.compare_button.setText("🔍 Reference Comparison View")
                self.hide_overlay_checkbox.setVisible(False)
        else:
            # Clear reference image completely
            self.reference_image_path = None
            self.reference_image.image_pixmap = None
            self.reference_image.checkboxes = []
            self.reference_image.clear()
            self.reference_image.setText("No reference image")
            self.hide_overlay_checkbox.setVisible(False)
            if not has_ref_video:
                self.compare_button.setEnabled(False)
        
        # Enable compare button if we have a ref video or ref image + camera
        if has_ref_video:
            self.compare_button.setEnabled(bool(self.current_camera))
            self.compare_button.setText("🔍 Reference Comparison View")
            self.hide_overlay_checkbox.setVisible(False)
        
        # Show/hide pass/fail buttons based on step requirement
        self.pass_fail_widget.setVisible(step.get('require_pass_fail', False))
        
        # Enable/disable compare button
        if not has_ref_video:
            self.compare_button.setEnabled(bool(self.reference_image_path and self.current_camera))
        
        # Update step status
        photo_required = step.get('require_photo', False)
        required_photo_count = step.get('required_photo_count', 1)
        annotations_required = step.get('require_annotations', False)
        
        status_parts = []
        if photo_required:
            status_parts.append(f"Photos: {len(self.step_images)}/{required_photo_count} required")
        if annotations_required:
            # Check if any captured image has markers
            has_markers = any(img.get('markers') and len(img.get('markers', [])) > 0 
                            for img in self.step_images)
            if has_markers:
                status_parts.append("Annotations: ✓ Added")
            else:
                status_parts.append("Annotations: ⚠ Required (click preview to add markers)")
        
        # Show checkbox status if present
        if checkbox_data:
            checked = self.reference_image.get_checked_count()
            total = self.reference_image.get_total_count()
            if checked == total:
                status_parts.append(f"Inspection: ✓ {checked}/{total} checked")
            else:
                status_parts.append(f"Inspection: ⚠ {checked}/{total} checked")
        
        # Show step result if marked
        if self.current_step in self.step_results:
            result = "✓ PASS" if self.step_results[self.current_step] else "✗ FAIL"
            status_parts.append(f"Result: {result}")
        
        self.step_status.setText(" | ".join(status_parts) if status_parts else "Optional documentation")
    
    def update_step_status(self):
        """Update just the status display without reloading step."""
        if not self.workflow or 'steps' not in self.workflow:
            return
        
        steps = self.workflow['steps']
        if self.current_step >= len(steps):
            return
        
        step = steps[self.current_step]
        checkbox_data = step.get('inspection_checkboxes', [])
        
        photo_required = step.get('require_photo', False)
        required_photo_count = step.get('required_photo_count', 1)
        annotations_required = step.get('require_annotations', False)
        
        status_parts = []
        if photo_required:
            status_parts.append(f"Photos: {len(self.step_images)}/{required_photo_count} required")
        if annotations_required:
            has_markers = any(img.get('markers') and len(img.get('markers', [])) > 0 
                            for img in self.step_images)
            if has_markers:
                status_parts.append("Annotations: ✓ Added")
            else:
                status_parts.append("Annotations: ⚠ Required (click preview to add markers)")
        
        if checkbox_data:
            checked = self.reference_image.get_checked_count()
            total = self.reference_image.get_total_count()
            if checked == total:
                status_parts.append(f"Inspection: ✓ {checked}/{total} checked")
            else:
                status_parts.append(f"Inspection: ⚠ {checked}/{total} checked")
        
        # Show step result if marked
        if self.current_step in self.step_results:
            result = "✓ PASS" if self.step_results[self.current_step] else "✗ FAIL"
            status_parts.append(f"Result: {result}")
        
        self.step_status.setText(" | ".join(status_parts) if status_parts else "Optional documentation")
        
        # Update navigation buttons
        self.prev_button.setEnabled(self.current_step > 0)
        
        is_last_step = self.current_step == len(steps) - 1
        self.next_button.setVisible(not is_last_step)
        self.finish_button.setVisible(is_last_step)
    
    def on_checkboxes_changed(self, checked, total):
        """Handle checkbox status change."""
        self.update_step_status()
    
    def update_breadcrumb(self):
        """Update step breadcrumb navigation."""
        # Clear existing breadcrumb
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.workflow or 'steps' not in self.workflow:
            return
        
        steps = self.workflow['steps']
        for i in range(len(steps)):
            # Determine step status
            if i <= self.max_step_reached and i != self.current_step:
                # Visited step - check if passed
                if i in self.step_results:
                    status = "✓" if self.step_results[i] else "✗"
                    color = "#4CAF50" if self.step_results[i] else "#F44336"
                elif i in self.step_checkbox_states:
                    checkbox_states = self.step_checkbox_states[i]
                    if isinstance(checkbox_states, list):
                        checked_count = sum(1 for cb in checkbox_states if cb.get('checked', False))
                        if checked_count == len(checkbox_states):
                            status = "✓"
                            color = "#4CAF50"
                        else:
                            status = "✗"
                            color = "#F44336"
                    else:
                        status = "✓"
                        color = "#81C784"
                elif i < self.current_step:
                    status = "✓"
                    color = "#81C784"
                else:
                    # Visited but ahead of current (user navigated back)
                    status = str(i + 1)
                    color = "#81C784"
            elif i == self.current_step:
                status = str(i + 1)
                color = "#77C25E"
            else:
                status = str(i + 1)
                color = "#CCCCCC"
            
            # Create step indicator
            step_btn = QPushButton(status)
            step_btn.setFixedSize(30, 30)
            clickable = i <= self.max_step_reached and i != self.current_step
            if clickable:
                step_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        color: white;
                        border: none;
                        border-radius: 15px;
                        font-weight: bold;
                        font-size: 10pt;
                    }}
                    QPushButton:hover {{
                        border: 2px solid white;
                    }}
                """)
                step_btn.setCursor(Qt.PointingHandCursor)
                step_btn.setToolTip(f"Go to Step {i + 1}: {steps[i].get('title', '')}")
                step_btn.clicked.connect(lambda checked, idx=i: self.go_to_step(idx))
            else:
                step_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        color: white;
                        border: none;
                        border-radius: 15px;
                        font-weight: bold;
                        font-size: 10pt;
                    }}
                """)
                step_btn.setEnabled(False)
            self.breadcrumb_layout.addWidget(step_btn)
            
            # Add arrow between steps
            if i < len(steps) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #888888; font-size: 12pt;")
                self.breadcrumb_layout.addWidget(arrow)
        
        self.breadcrumb_layout.addStretch()
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        # Space: Capture image
        if event.key() == Qt.Key_Space and self.capture_button.isEnabled() and not self.notes_input.hasFocus():
            self.capture_image()
            event.accept()
        # Enter/Return: Advance to next step (only if not typing in notes)
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and not self.notes_input.hasFocus():
            if self.finish_button.isVisible():
                self.finish_workflow()
            elif self.next_button.isEnabled():
                self.next_step()
            event.accept()
        # R: Toggle recording
        elif event.key() == Qt.Key_R and self.record_button.isEnabled() and not self.notes_input.hasFocus():
            self.toggle_recording()
            event.accept()
        # B: Scan barcode
        elif event.key() == Qt.Key_B and self.scan_button.isEnabled() and not self.notes_input.hasFocus():
            self.scan_barcode()
            event.accept()
        # Ctrl+Z: Undo checkbox
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            if hasattr(self, 'reference_image') and hasattr(self.reference_image, 'undo_checkbox'):
                self.reference_image.undo_checkbox()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def capture_image(self):
        """Capture image for current step."""
        if not self.current_camera:
            return
        
        frame = self.current_camera.capture_frame()
        if frame is not None:
            # Check if current step has PNG overlay with alpha
            has_alpha = False
            if self.workflow and self.reference_image_path and os.path.exists(self.reference_image_path):
                ref_test = cv2.imread(self.reference_image_path, cv2.IMREAD_UNCHANGED)
                has_alpha = ref_test is not None and len(ref_test.shape) == 3 and ref_test.shape[2] == 4
            
            # Apply overlay if present and not hidden
            if has_alpha and not self.hide_overlay_checkbox.isChecked():
                frame = self._render_overlay_on_frame(frame, self.reference_image_path, has_alpha)
            
            # Draw markers
            markers = self.preview_label.get_markers_data()
            if markers:
                frame = self._draw_markers_on_frame(frame, markers, self._get_marker_bgr_color())
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            serial_prefix = self.serial_number if self.serial_number else "unknown"
            step_name = self.workflow['steps'][self.current_step].get('title', f'step{self.current_step + 1}')
            filename = f"{serial_prefix}_{step_name}_{timestamp}.jpg"
            filepath = os.path.join(self.output_dir, filename)
            
            cv2.imwrite(filepath, frame)
            
            notes = self.notes_input.text().strip()
            camera_name = self.current_camera.name if self.current_camera else "Unknown"
            
            image_data = {
                'path': filepath,
                'camera': camera_name,
                'notes': notes,
                'timestamp': timestamp,
                'type': 'image',
                'markers': markers,
                'step': self.current_step + 1,
                'step_title': step_name
            }
            
            self.captured_images.append(image_data)
            self.step_images.append(image_data)
            
            self.notes_input.clear()
            self.preview_label.clear_markers()
            
            self.update_step_status()  # Update status only, don't reload step
            
            QMessageBox.information(self, "Image Captured", 
                                   f"Image saved for step {self.current_step + 1}")
    
    def on_barcode_detected(self, barcode_type: str, barcode_data: str):
        """Handle barcode detection (just update status, don't auto-append)."""
        logger.info(f"Barcode detected: {barcode_type} - {barcode_data}")
    
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
        
        # Add to scans list for current step
        scan_info = {
            'type': barcode_type,
            'data': barcode_data,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'step': self.current_step + 1
        }
        self.step_barcode_scans.append(scan_info)
        self.all_barcode_scans.append(scan_info)
        
        # Capture current frame
        if self.current_camera:
            frame = self.current_camera.capture_frame()
            if frame is not None:
                # Save image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                serial_prefix = self.serial_number if self.serial_number else "unknown"
                step_name = self.workflow['steps'][self.current_step].get('title', f'step{self.current_step + 1}')
                filename = f"{serial_prefix}_{step_name}_barcode_{timestamp}.jpg"
                filepath = os.path.join(self.output_dir, filename)
                cv2.imwrite(filepath, frame)
                
                # Add to captured images with barcode note
                image_data = {
                    'path': filepath,
                    'camera': self.current_camera.name,
                    'notes': f"Barcode scan capture ({barcode_type}): {barcode_data}",
                    'timestamp': timestamp,
                    'type': 'image',
                    'markers': [],
                    'barcode_scans': [scan_info],
                    'step': self.current_step + 1,
                    'step_title': step_name
                }
                self.captured_images.append(image_data)
                self.step_images.append(image_data)
        
        # Show dialog
        step_scan_count = len(self.step_barcode_scans)
        msg = QMessageBox(self)
        msg.setWindowTitle("Barcode Scanned")
        msg.setText(f"Barcode Type: {barcode_type}\nData: {barcode_data}\n\nScan {step_scan_count} for this step")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
        
        self.update_step_status()
        logger.info(f"Barcode scanned ({step_scan_count} total for step)")
    
    def on_usb_barcode_scanned(self, barcode_data):
        """Handle barcode from USB HID scanner - same data path as camera scan."""
        scan_info = {
            'type': 'USB-HID',
            'data': barcode_data,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'step': self.current_step + 1
        }
        self.step_barcode_scans.append(scan_info)
        self.all_barcode_scans.append(scan_info)
        
        # Capture current frame if camera is active
        if self.current_camera:
            frame = self.current_camera.capture_frame()
            if frame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                serial_prefix = self.serial_number if self.serial_number else "unknown"
                step_name = self.workflow['steps'][self.current_step].get('title', f'step{self.current_step + 1}')
                filename = f"{serial_prefix}_{step_name}_barcode_{timestamp}.jpg"
                filepath = os.path.join(self.output_dir, filename)
                cv2.imwrite(filepath, frame)
                
                image_data = {
                    'path': filepath,
                    'camera': self.current_camera.name,
                    'notes': f"USB barcode scan: {barcode_data}",
                    'timestamp': timestamp,
                    'type': 'image',
                    'markers': [],
                    'barcode_scans': [scan_info],
                    'step': self.current_step + 1,
                    'step_title': step_name
                }
                self.captured_images.append(image_data)
                self.step_images.append(image_data)
        
        step_scan_count = len(self.step_barcode_scans)
        msg = QMessageBox(self)
        msg.setWindowTitle("USB Barcode Scanned")
        msg.setText(f"Barcode Data: {barcode_data}\n\nScan {step_scan_count} for this step")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
        
        self.update_step_status()
        logger.info(f"USB barcode scanned ({step_scan_count} total for step)")

    def open_review_dialog(self):
        """Open review captures dialog."""
        if not self.captured_images:
            QMessageBox.information(self, "No Captures", "No images or videos have been captured yet.")
            return
        
        # Get current step requirements
        step = self.workflow['steps'][self.current_step]
        requirements = {
            'require_photo': step.get('require_photo', False),
            'required_photo_count': step.get('required_photo_count', 1),
            'require_annotations': step.get('require_annotations', False)
        }
        
        dialog = ReviewCapturesDialog(
            self.captured_images, 
            self.step_images, 
            requirements,
            parent=self
        )
        dialog.exec_()
        
        # Update status after review
        self.update_step_status()
    
    def open_camera_settings(self):
        """Open camera settings dialog."""
        dialog = CameraSettingsDialog(self.available_cameras, parent=self)
        dialog.exec_()
    
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
        """Draw annotation markers on frame."""
        return draw_markers_on_frame(frame, markers, color)
    
    def _render_overlay_on_frame(self, frame, reference_image_path, has_alpha=False):
        """Render overlay on frame using current transform settings."""
        cache = {'params': self._overlay_cache_params, 'canvas': self._overlay_cache}
        result = render_overlay_on_frame(
            frame, reference_image_path, has_alpha,
            self.overlay_scale, self.overlay_x_offset,
            self.overlay_y_offset, self.overlay_rotation,
            self.overlay_transparency, cache)
        self._overlay_cache_params = cache.get('params')
        self._overlay_cache = cache.get('canvas')
        return result
    
    def _draw_reference_annotations(self, img, checkboxes, markers):
        """Draw checkboxes and markers on reference image."""
        return draw_reference_annotations(img, checkboxes, markers)
    
    def mark_step_result(self, passed):
        """Mark current step as pass or fail."""
        self.step_results[self.current_step] = passed
        self.update_step_status()
        
        result_text = "PASS" if passed else "FAIL"
        QMessageBox.information(self, "Step Marked", 
                               f"Step {self.current_step + 1} marked as {result_text}")
    
    def _save_current_step_state(self):
        """Save checkbox state and overlay transforms for the current step before navigating away."""
        step = self.workflow['steps'][self.current_step]
        if step.get('inspection_checkboxes'):
            self.step_checkbox_states[self.current_step] = [
                {'x': cb['x'], 'y': cb['y'], 'checked': cb['checked']}
                for cb in self.reference_image.checkboxes
            ]
        # Persist overlay transforms to workflow JSON if this step uses an overlay
        if step.get('transparent_overlay') and self.reference_image_path:
            transforms = {
                'scale': self.overlay_scale,
                'x_offset': self.overlay_x_offset,
                'y_offset': self.overlay_y_offset,
                'rotation': self.overlay_rotation,
                'transparency': self.overlay_transparency
            }
            defaults = {'scale': 100, 'x_offset': 0, 'y_offset': 0, 'rotation': 0, 'transparency': 100}
            if transforms != defaults or 'overlay_transforms' in step:
                step['overlay_transforms'] = transforms
                self._save_workflow_json()
        self.save_progress()

    def _load_step_data(self, step_index):
        """Rebuild step_images and step_barcode_scans for the given step."""
        step_num = step_index + 1
        self.step_images = [img for img in self.captured_images if img.get('step') == step_num]
        self.step_barcode_scans = [s for s in getattr(self, 'all_barcode_scans', []) if s.get('step') == step_num]

    def _save_workflow_json(self):
        """Atomically write the workflow back to its JSON file."""
        try:
            dir_name = os.path.dirname(self.workflow_path)
            fd, tmp_path = tempfile.mkstemp(suffix='.json', dir=dir_name)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self.workflow, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.workflow_path)
        except Exception as e:
            logger.warning(f"Could not save overlay transforms to workflow: {e}")
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def previous_step(self):
        """Go to previous step."""
        if self.current_step > 0:
            self._save_current_step_state()
            self.current_step -= 1
            self._load_step_data(self.current_step)
            self.show_current_step()

    def go_to_step(self, step_index):
        """Jump to a previously visited step via breadcrumb click."""
        if step_index == self.current_step or step_index < 0 or step_index > self.max_step_reached:
            return
        self._save_current_step_state()
        self.current_step = step_index
        self._load_step_data(self.current_step)
        self.show_current_step()
    
    def next_step(self):
        """Go to next step."""
        if not self.validate_step():
            return
        
        self._save_current_step_state()
        
        if self.current_step < len(self.workflow['steps']) - 1:
            self.current_step += 1
            self.max_step_reached = max(self.max_step_reached, self.current_step)
            self._load_step_data(self.current_step)
            self.show_current_step()
    
    def save_progress(self):
        """Save current workflow progress."""
        success = save_workflow_progress(
            self.output_dir, self.workflow_path, self.current_step,
            self.step_results, self.step_checkbox_states,
            self.captured_images, self.recorded_videos,
            self.serial_number, self.technician, self.description)
        if success:
            self.autosave_label.setText("✓ Progress saved")
            QTimer.singleShot(2000, lambda: self.autosave_label.setText(""))
    
    def _deferred_load_progress(self):
        """Load progress after widget is fully constructed and signals connected."""
        self.load_progress()
        self.show_current_step()
        self.update_breadcrumb()

    def load_progress(self):
        """Load saved workflow progress if exists."""
        result = load_workflow_progress(self.output_dir, self.workflow_path)

        if result is None:
            return
        
        if result == 'corrupted':
            QMessageBox.warning(self, "Corrupted Progress File",
                              "The saved progress file is corrupted and cannot be loaded.\n\n"
                              "Starting workflow from the beginning.")
            return

        progress_data = result

        msg = QMessageBox(self)
        msg.setWindowTitle("Resume Progress?")
        msg.setText(f"Found saved progress at step {progress_data.get('current_step', 0) + 1}.")
        msg.setInformativeText("What would you like to do?")

        resume_btn = msg.addButton("Resume", QMessageBox.AcceptRole)
        report_btn = msg.addButton("Generate Partial Report", QMessageBox.ActionRole)
        start_fresh_btn = msg.addButton("Start from Beginning", QMessageBox.DestructiveRole)
        back_btn = msg.addButton("Back to Menu", QMessageBox.RejectRole)

        msg.exec_()

        if msg.clickedButton() == resume_btn:
            logger.info("Resuming workflow progress")
            self.current_step = progress_data.get('current_step', 0)
            self.max_step_reached = self.current_step
            self.step_results = progress_data.get('step_results', {})
            self.step_results = {int(k): v for k, v in self.step_results.items()}
            self.step_checkbox_states = progress_data.get('step_checkbox_states', {})
            self.step_checkbox_states = {int(k): v for k, v in self.step_checkbox_states.items()}
            self.captured_images = progress_data.get('captured_images', [])
            self.recorded_videos = progress_data.get('recorded_videos', [])
        elif msg.clickedButton() == report_btn:
            logger.info("Generating partial report from progress")
            self.step_results = progress_data.get('step_results', {})
            self.step_results = {int(k): v for k, v in self.step_results.items()}
            self.step_checkbox_states = progress_data.get('step_checkbox_states', {})
            self.step_checkbox_states = {int(k): v for k, v in self.step_checkbox_states.items()}
            self.captured_images = progress_data.get('captured_images', [])
            self.recorded_videos = progress_data.get('recorded_videos', [])

            self.generate_workflow_report()

            clear_workflow_progress(self.output_dir)
            QMessageBox.information(self, "Partial Report Generated",
                                  "Partial report has been generated.\n\nReturning to menu...")
            self.cleanup_resources()
            self.back_requested.emit()
            return
        elif msg.clickedButton() == start_fresh_btn:
            logger.info("User chose to start from beginning, deleting progress file")
            clear_workflow_progress(self.output_dir)
            QMessageBox.information(self, "Starting Fresh",
                                  "Progress file deleted. Starting workflow from the beginning.")
        else:
            logger.info("User chose to go back to menu, keeping progress file")
            self.cleanup_resources()
            self.back_requested.emit()
            return
    
    def clear_progress(self):
        """Clear saved progress file."""
        clear_workflow_progress(self.output_dir)
    
    def validate_step(self):
        """Validate current step requirements."""
        step = self.workflow['steps'][self.current_step]
        
        if step.get('require_photo', False):
            required_count = step.get('required_photo_count', 1)
            if len(self.step_images) < required_count:
                QMessageBox.warning(self, "Photo Required", 
                                   f"This step requires {required_count} photo(s) before proceeding.\n"
                                   f"Currently captured: {len(self.step_images)}")
                return False
        
        if step.get('require_annotations', False):
            has_annotations = any(img.get('markers') and len(img.get('markers', [])) > 0 
                                 for img in self.step_images)
            if not has_annotations:
                QMessageBox.warning(self, "Annotations Required", 
                                   "This step requires annotations (markers) on captured images.\n\n"
                                   "Click on the camera preview to add markers (A, B, C...) before capturing.")
                return False
        
        if step.get('require_barcode_scan', False) and len(self.step_barcode_scans) == 0:
            QMessageBox.warning(self, "Barcode Scan Required", 
                               "This step requires at least one barcode scan before proceeding.\n\n"
                               "Use the 'Scan Barcode/QR' button when a barcode is detected.")
            return False
        
        if step.get('require_pass_fail', False) and self.current_step not in self.step_results:
            QMessageBox.warning(self, "Pass/Fail Required", 
                               "This step requires you to mark it as Pass or Fail before proceeding.")
            return False
        
        return True
    
    def on_back_clicked(self):
        """Handle back to menu button click."""
        if not self.captured_images:
            self.cleanup_resources()
            self.back_requested.emit()
            return
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Leave Workflow")
        msg.setText("You have captured data in this workflow. What would you like to do?")
        
        save_btn = msg.addButton("Save Progress", QMessageBox.AcceptRole)
        save_btn.setToolTip("Save a progress file to resume later")
        report_btn = msg.addButton("Generate Partial Report", QMessageBox.ActionRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
        
        msg.setInformativeText(
            "Save Progress: Creates a progress file you can resume from the main menu.\n"
            "Generate Partial Report: Creates a PDF/DOCX report with data captured so far."
        )
        
        msg.exec_()
        
        if msg.clickedButton() == cancel_btn:
            return
        elif msg.clickedButton() == save_btn:
            self._save_current_step_state()
            QMessageBox.information(self, "Progress Saved",
                                   "Your progress has been saved.\n\n"
                                   "You can resume this workflow from the main menu.")
        elif msg.clickedButton() == report_btn:
            try:
                all_barcode_scans = []
                for img in self.captured_images:
                    if 'barcode_scans' in img:
                        all_barcode_scans.extend(img['barcode_scans'])
                
                workflow_name = self.workflow.get('name', 'Workflow')
                pdf_path, docx_path = generate_reports(
                    serial_number=self.serial_number,
                    technician=self.technician,
                    description=self.description,
                    images=self.captured_images,
                    mode_name=workflow_name,
                    workflow_name=workflow_name,
                    video_paths=self.recorded_videos,
                    barcode_scans=all_barcode_scans if all_barcode_scans else None
                )
                self.show_report_dialog(pdf_path, docx_path, len(self.captured_images))
            except Exception as e:
                QMessageBox.warning(self, "Report Error",
                                   f"Failed to generate report:\n{str(e)}")
            
            # Clean up progress file since report was generated
            progress_file = os.path.join(self.output_dir, "_workflow_progress.json")
            if os.path.exists(progress_file):
                try:
                    os.remove(progress_file)
                except OSError:
                    pass
        
        self.cleanup_resources()
        self.back_requested.emit()
    
    def finish_workflow(self):
        """Complete the workflow."""
        if not self.validate_step():
            return
        
        # Auto-generate report
        try:
            pdf_path, docx_path = self.generate_workflow_report()
            
            # Show enhanced report dialog
            self.show_report_dialog(pdf_path, docx_path, len(self.captured_images))
        except Exception as e:
            QMessageBox.warning(
                self,
                "Report Error",
                f"Workflow complete but report generation failed:\n{str(e)}"
            )
        
        self.clear_progress()  # Clear saved progress
        self.cleanup_resources()
        self.back_requested.emit()
    
    def show_report_dialog(self, pdf_path, docx_path, image_count):
        """Show enhanced report dialog with view options."""
        show_report_dialog(self, pdf_path, docx_path, image_count)
    
    def _generate_checkbox_image(self, ref_image_path, checkboxes, step_index):
        """Generate an image showing the reference with checkbox completion status."""
        return generate_checkbox_image(ref_image_path, checkboxes, step_index,
                                       self.output_dir, self.serial_number)
    
    def generate_workflow_report(self):
        """Generate PDF report for completed workflow."""
        try:
            return generate_workflow_report(self)
        except Exception as e:
            QMessageBox.critical(self, "Report Error",
                                f"Failed to generate report:\n{str(e)}")
            raise
    
    def show_reference_fullsize(self):
        """Show reference image in full size popup with interactive checkboxes."""
        show_reference_fullsize(self)
    
    def show_comparison(self):
        """Show side-by-side comparison of reference and live camera."""
        if not self.current_camera:
            return

        has_ref_video = bool(self.ref_video_path and os.path.exists(self.ref_video_path))
        has_ref_image = bool(self.reference_image_path and os.path.exists(self.reference_image_path))

        if not has_ref_video and not has_ref_image:
            return

        if has_ref_video:
            show_video_comparison(self)
        else:
            show_overlay_comparison(self)

    # --- Reference video player methods ---

    def _open_ref_video(self, path):
        """Open a reference video file for playback using background decoder thread."""
        self._close_ref_video()
        self.ref_video_path = path
        self._ref_video_playing = False
        thread = VideoDecoderThread(path, self)
        thread.frame_ready.connect(self._on_ref_video_frame)
        thread.start()
        self._ref_video_thread = thread
        self.ref_video_play_btn.setText("▶ Play")

    def _close_ref_video(self):
        """Stop and release reference video thread."""
        if self._ref_video_thread:
            self._ref_video_thread.stop_thread()
            self._ref_video_thread = None
        self._ref_video_playing = False

    def _on_ref_video_frame(self, qimg, pos_ms, duration_ms):
        """Receive a decoded frame from the background thread."""
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.ref_video_display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation)
        self.ref_video_display.setPixmap(pixmap)
        if not self._ref_video_slider_dragging:
            self.ref_video_slider.blockSignals(True)
            self.ref_video_slider.setMaximum(max(duration_ms, 1))
            self.ref_video_slider.setValue(pos_ms)
            self.ref_video_slider.blockSignals(False)
        self.ref_video_time_label.setText(
            f"{self._fmt_ms(pos_ms)} / {self._fmt_ms(duration_ms)}")
        # Update button if playback ended
        if not self._ref_video_thread or not self._ref_video_thread._playing:
            if self._ref_video_playing:
                self._ref_video_playing = False
                self.ref_video_play_btn.setText("▶ Play")

    def _toggle_ref_video(self):
        """Play or pause the reference video."""
        if not self._ref_video_thread:
            return
        if self._ref_video_playing:
            self._ref_video_thread.pause()
            self._ref_video_playing = False
            self.ref_video_play_btn.setText("▶ Play")
        else:
            self._ref_video_thread.play()
            self._ref_video_playing = True
            self.ref_video_play_btn.setText("⏸ Pause")

    def _restart_ref_video(self):
        """Restart the reference video from the beginning."""
        if not self._ref_video_thread:
            return
        self._ref_video_thread.seek(0)
        self._ref_video_thread.play()
        self._ref_video_playing = True
        self.ref_video_play_btn.setText("⏸ Pause")

    def _ref_video_slider_pressed(self):
        self._ref_video_slider_dragging = True

    def _ref_video_slider_released(self):
        self._ref_video_slider_dragging = False
        if self._ref_video_thread:
            self._ref_video_thread.seek(self.ref_video_slider.value())

    def _ref_video_slider_moved(self, position):
        """Seek while dragging the slider."""
        if self._ref_video_thread:
            self._ref_video_thread.seek(position)

    @staticmethod
    def _fmt_ms(ms):
        """Format milliseconds as m:ss."""
        s = max(0, ms) // 1000
        return f"{s // 60}:{s % 60:02d}"

    def cleanup_resources(self):
        """Clean up camera resources."""
        self._close_ref_video()
        
        if self.timer.isActive():
            self.timer.stop()
        
        if self.barcode_check_timer and self.barcode_check_timer.isActive():
            self.barcode_check_timer.stop()
        
        if self.qr_scanner:
            self.qr_scanner.stop()
            self.qr_scanner = None
        
        if self.current_camera:
            self.current_camera.close()
            self.current_camera = None
    
    def closeEvent(self, event):
        """Handle window close."""
        self.cleanup_resources()
        event.accept()
