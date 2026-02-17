"""Workflow execution screen for guided QC and maintenance procedures."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QMessageBox, QLineEdit, QSplitter, QComboBox)
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


class WorkflowExecutionScreen(QWidget):
    """Execute a workflow step-by-step with camera integration."""
    
    back_requested = pyqtSignal()
    
    def __init__(self, workflow_path, serial_number, description):
        super().__init__()
        self.workflow_path = workflow_path
        self.serial_number = serial_number
        self.description = description
        self.current_step = 0
        self.workflow = None
        self.current_camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.qr_scanner = None
        self.captured_images = []  # All images from workflow
        self.step_images = []  # Images for current step
        
        # Setup output directory
        output_serial = serial_number if serial_number else "unknown"
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "output", "captured_images", output_serial)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.load_workflow()
        self.init_ui()
        self.discover_cameras()
        self.show_current_step()
    
    def load_workflow(self):
        """Load workflow from JSON file."""
        try:
            with open(self.workflow_path, 'r') as f:
                self.workflow = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load workflow: {e}")
            self.workflow = {"name": "Error", "steps": []}
    
    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            background-color: #77C25E;
            border-radius: 5px;
        """)
        header_layout = QVBoxLayout(header_widget)
        
        title = QLabel(self.workflow.get('name', 'Workflow'))
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        header_layout.addWidget(title)
        
        self.step_label = QLabel()
        self.step_label.setFont(QFont("Arial", 12))
        self.step_label.setStyleSheet("color: white; background: transparent;")
        header_layout.addWidget(self.step_label)
        
        main_layout.addWidget(header_widget)
        
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
        left_layout.addWidget(self.instructions_text)
        
        ref_label = QLabel("Reference Image:")
        ref_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        left_layout.addWidget(ref_label)
        
        self.reference_image = QLabel()
        self.reference_image.setMinimumSize(300, 200)
        self.reference_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reference_image.setStyleSheet("border: 2px solid #CCCCCC;")
        self.reference_image.setText("No reference image")
        left_layout.addWidget(self.reference_image)
        
        splitter.addWidget(left_widget)
        
        # Right side - Camera view
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Camera selection
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Camera:")
        camera_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addStretch()
        right_layout.addLayout(camera_layout)
        
        # Camera preview
        self.preview_label = AnnotatablePreview()
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("border: 2px solid #77C25E; background-color: #2b2b2b;")
        self.preview_label.setText("No camera selected")
        right_layout.addWidget(self.preview_label)
        
        # Annotation controls
        annotation_layout = QHBoxLayout()
        self.clear_markers_button = QPushButton("Clear Markers")
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
        
        annotation_help = QLabel("Click: Add | Drag: Move | Scroll: Rotate | Right-click: Remove")
        annotation_help.setStyleSheet("color: #888888; font-size: 10px;")
        annotation_layout.addWidget(annotation_help)
        annotation_layout.addStretch()
        right_layout.addLayout(annotation_layout)
        
        # Notes input
        notes_layout = QHBoxLayout()
        notes_label = QLabel("Notes:")
        notes_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Add notes for this step...")
        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(self.notes_input)
        right_layout.addLayout(notes_layout)
        
        # Capture button
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.setMinimumHeight(40)
            }
        """)
        self.capture_button.clicked.connect(self.capture_image)
        self.capture_button.setEnabled(False)
        right_layout.addWidget(self.capture_button)
        
        self.step_status = QLabel()
        self.step_status.setStyleSheet("color: #888888; font-size: 11px;")
        right_layout.addWidget(self.step_status)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("← Previous Step")
        self.prev_button.setMinimumHeight(50)
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
            cameras = CameraManager.discover_cameras()
            for cam in cameras:
                cam.close()
            
            self.camera_combo.clear()
            self.available_cameras = cameras
            
            for cam in cameras:
                self.camera_combo.addItem(cam.name)
        except Exception as e:
            print(f"Camera discovery error: {e}")
            self.available_cameras = []
    
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
                if self.current_camera.open():
                    self.timer.start(30)
                    self.capture_button.setEnabled(True)
        except Exception as e:
            print(f"Camera error: {e}")
    
    def update_frame(self):
        """Update camera preview."""
        if not self.current_camera:
            return
        
        frame = self.current_camera.capture_frame()
        if frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.preview_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.set_frame(scaled_pixmap)
    
    def show_current_step(self):
        """Display the current step information."""
        if not self.workflow or 'steps' not in self.workflow:
            return
        
        steps = self.workflow['steps']
        if self.current_step >= len(steps):
            return
        
        step = steps[self.current_step]
        
        # Update header
        self.step_label.setText(f"Step {self.current_step + 1} of {len(steps)}: {step.get('title', 'Untitled')}")
        
        # Update instructions
        self.instructions_text.setText(step.get('instructions', 'No instructions provided.'))
        
        # Update reference image
        ref_image_path = step.get('reference_image', '')
        if ref_image_path and os.path.exists(ref_image_path):
            pixmap = QPixmap(ref_image_path)
            scaled = pixmap.scaled(self.reference_image.size(), 
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.reference_image.setPixmap(scaled)
        else:
            self.reference_image.clear()
            self.reference_image.setText("No reference image")
        
        # Update step status
        photo_required = step.get('require_photo', False)
        annotations_required = step.get('require_annotations', False)
        
        status_parts = []
        if photo_required:
            status_parts.append(f"Photos: {len(self.step_images)}/1 required")
        if annotations_required:
            status_parts.append("Annotations required")
        
        self.step_status.setText(" | ".join(status_parts) if status_parts else "Optional documentation")
        
        # Update navigation buttons
        self.prev_button.setEnabled(self.current_step > 0)
        
        is_last_step = self.current_step == len(steps) - 1
        self.next_button.setVisible(not is_last_step)
        self.finish_button.setVisible(is_last_step)
    
    def capture_image(self):
        """Capture image for current step."""
        if not self.current_camera:
            return
        
        frame = self.current_camera.capture_frame()
        if frame is not None:
            markers = self.preview_label.get_markers_data()
            
            if markers:
                frame = self._draw_markers_on_frame(frame, markers)
            
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
            
            self.show_current_step()  # Update status
            
            QMessageBox.information(self, "Image Captured", 
                                   f"Image saved for step {self.current_step + 1}")
    
    def _draw_markers_on_frame(self, frame, markers):
        """Draw annotation markers on frame."""
        preview_size = self.preview_label.size()
        frame_h, frame_w = frame.shape[:2]
        
        scale_x = frame_w / preview_size.width()
        scale_y = frame_h / preview_size.height()
        
        for marker in markers:
            x = int(marker['x'] * scale_x)
            y = int(marker['y'] * scale_y)
            label = marker['label']
            angle = marker.get('angle', 45)
            
            arrow_length = 30
            angle_rad = np.radians(angle)
            end_x = int(x + arrow_length * np.cos(angle_rad))
            end_y = int(y + arrow_length * np.sin(angle_rad))
            
            cv2.arrowedLine(frame, (x, y), (end_x, end_y), (0, 0, 255), 2, tipLength=0.3)
            cv2.circle(frame, (end_x, end_y), 12, (255, 255, 255), -1)
            cv2.circle(frame, (end_x, end_y), 12, (0, 0, 255), 2)
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(label, font, 0.5, 2)[0]
            text_x = end_x - text_size[0] // 2
            text_y = end_y + text_size[1] // 2
            cv2.putText(frame, label, (text_x, text_y), font, 0.5, (0, 0, 255), 2)
        
        return frame
    
    def previous_step(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.step_images = []  # Clear images for new step
            self.show_current_step()
    
    def next_step(self):
        """Go to next step."""
        if not self.validate_step():
            return
        
        if self.current_step < len(self.workflow['steps']) - 1:
            self.current_step += 1
            self.step_images = []  # Clear images for new step
            self.show_current_step()
    
    def validate_step(self):
        """Validate current step requirements."""
        step = self.workflow['steps'][self.current_step]
        
        if step.get('require_photo', False) and len(self.step_images) == 0:
            QMessageBox.warning(self, "Photo Required", 
                               "This step requires at least one photo before proceeding.")
            return False
        
        if step.get('require_annotations', False):
            has_annotations = any(img.get('markers') for img in self.step_images)
            if not has_annotations:
                QMessageBox.warning(self, "Annotations Required", 
                                   "This step requires annotations on captured images.")
                return False
        
        return True
    
    def finish_workflow(self):
        """Complete the workflow."""
        if not self.validate_step():
            return
        
        reply = QMessageBox.question(self, "Finish Workflow", 
                                    f"Workflow complete!\n\n"
                                    f"Total images captured: {len(self.captured_images)}\n\n"
                                    f"Generate report?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.generate_workflow_report()
        
        self.cleanup_resources()
        self.back_requested.emit()
    
    def generate_workflow_report(self):
        """Generate PDF report for completed workflow."""
        try:
            # Determine mode name for report
            workflow_name = self.workflow.get('name', 'Workflow')
            
            # Create checklist from steps
            checklist_data = []
            for i, step in enumerate(self.workflow['steps']):
                step_title = step.get('title', f'Step {i+1}')
                # Count images for this step
                step_imgs = [img for img in self.captured_images if img.get('step') == i+1]
                passed = len(step_imgs) > 0  # Step passed if at least one image captured
                checklist_data.append({
                    'name': step_title,
                    'passed': passed
                })
            
            # Generate both PDF and DOCX reports
            pdf_path, docx_path = generate_reports(
                serial_number=self.serial_number,
                description=self.description,
                images=self.captured_images,
                mode_name=workflow_name,
                workflow_name=workflow_name,
                checklist_data=checklist_data
            )
            
            QMessageBox.information(self, "Reports Generated", 
                                   f"PDF and DOCX reports generated successfully!\n\n"
                                   f"PDF: {pdf_path}\n\n"
                                   f"DOCX: {docx_path}\n\n"
                                   f"Images: {len(self.captured_images)}\n"
                                   f"Steps completed: {len(checklist_data)}")
        
        except Exception as e:
            QMessageBox.critical(self, "Report Error", 
                               f"Failed to generate report:\n{str(e)}")
    
    def cleanup_resources(self):
        """Clean up camera resources."""
        if self.timer.isActive():
            self.timer.stop()
        
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
