"""Workflow execution screen for guided QC and maintenance procedures."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QMessageBox, QLineEdit, QSplitter, QComboBox, QDialog, QSizePolicy, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QColor, QPen
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


class InteractiveReferenceImage(QLabel):
    """Reference image with interactive checkboxes."""
    
    checkboxes_changed = pyqtSignal(int, int)  # checked_count, total_count
    
    def __init__(self):
        super().__init__()
        self.image_pixmap = None
        self.checkboxes = []  # List of {'x': %, 'y': %, 'checked': bool}
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
    
    def set_image_and_checkboxes(self, image_path, checkbox_data):
        """Load image and set up checkboxes."""
        if not image_path or not os.path.exists(image_path):
            self.clear()
            self.setText("No reference image")
            return
        
        self.image_pixmap = QPixmap(image_path)
        self.checkboxes = [{'x': cb['x'], 'y': cb['y'], 'checked': False} 
                          for cb in (checkbox_data or [])]
        self.update()
        self.emit_status()
    
    def mousePressEvent(self, event):
        """Toggle checkbox on click."""
        if not self.image_pixmap or not self.checkboxes:
            return
        
        # Find which checkbox was clicked
        click_pos = event.pos()
        for cb in self.checkboxes:
            cb_pos = self._get_checkbox_position(cb)
            if cb_pos and (cb_pos.x() - click_pos.x())**2 + (cb_pos.y() - click_pos.y())**2 < 400:
                cb['checked'] = not cb['checked']
                self.update()
                self.emit_status()
                break
    
    def _get_checkbox_position(self, checkbox):
        """Convert percentage position to widget pixels."""
        if not self.image_pixmap:
            return None
        
        # Calculate scaled image position
        widget_rect = self.rect()
        scaled_pixmap = self.image_pixmap.scaled(
            widget_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        x_offset = (widget_rect.width() - scaled_pixmap.width()) // 2
        y_offset = (widget_rect.height() - scaled_pixmap.height()) // 2
        
        x = x_offset + int(checkbox['x'] * scaled_pixmap.width())
        y = y_offset + int(checkbox['y'] * scaled_pixmap.height())
        
        return QPoint(x, y)
    
    def paintEvent(self, event):
        """Draw image and checkboxes."""
        super().paintEvent(event)
        
        if not self.image_pixmap:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw scaled image
        widget_rect = self.rect()
        scaled_pixmap = self.image_pixmap.scaled(
            widget_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        x_offset = (widget_rect.width() - scaled_pixmap.width()) // 2
        y_offset = (widget_rect.height() - scaled_pixmap.height()) // 2
        
        painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
        
        # Draw checkboxes
        for cb in self.checkboxes:
            pos = self._get_checkbox_position(cb)
            if pos:
                # Draw checkbox square
                if cb['checked']:
                    painter.setPen(QPen(QColor(119, 194, 94), 3))
                    painter.setBrush(QColor(119, 194, 94, 150))
                else:
                    painter.setPen(QPen(QColor(119, 194, 94), 2))
                    painter.setBrush(QColor(255, 255, 255, 200))
                
                painter.drawRect(pos.x() - 12, pos.y() - 12, 24, 24)
                
                # Draw checkmark if checked
                if cb['checked']:
                    painter.setPen(QPen(QColor(255, 255, 255), 3))
                    painter.drawLine(pos.x() - 6, pos.y(), pos.x() - 2, pos.y() + 6)
                    painter.drawLine(pos.x() - 2, pos.y() + 6, pos.x() + 8, pos.y() - 6)
        
        painter.end()
    
    def emit_status(self):
        """Emit checkbox status."""
        checked = sum(1 for cb in self.checkboxes if cb['checked'])
        total = len(self.checkboxes)
        self.checkboxes_changed.emit(checked, total)
    
    def get_checked_count(self):
        """Get number of checked boxes."""
        return sum(1 for cb in self.checkboxes if cb['checked'])
    
    def get_total_count(self):
        """Get total number of checkboxes."""
        return len(self.checkboxes)


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
        
        # Setup output directory - sanitize serial number for filesystem
        output_serial = self._sanitize_filename(serial_number) if serial_number else "unknown"
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "output", "captured_images", output_serial)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.load_workflow()
        self.init_ui()
        self.discover_cameras()
        self.show_current_step()
    
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
            with open(self.workflow_path, 'r') as f:
                self.workflow = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load workflow: {e}")
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
        
        self.reference_image = InteractiveReferenceImage()
        self.reference_image.setMinimumSize(300, 200)
        self.reference_image.setStyleSheet("border: 2px solid #CCCCCC;")
        self.reference_image.checkboxes_changed.connect(self.on_checkboxes_changed)
        self.reference_image_path = None  # Store current reference image path
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
        
        # Camera preview - larger and expandable
        self.preview_label = AnnotatablePreview()
        self.preview_label.setStyleSheet("border: 2px solid #77C25E; background-color: #2b2b2b;")
        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        right_layout.addWidget(self.preview_label, 1)  # Stretch factor 1 to take available space
        
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
        checkbox_data = step.get('inspection_checkboxes', [])
        
        if ref_image_path and os.path.exists(ref_image_path):
            self.reference_image_path = ref_image_path
            self.reference_image.set_image_and_checkboxes(ref_image_path, checkbox_data)
        else:
            self.reference_image_path = None
            self.reference_image.set_image_and_checkboxes(None, [])
        
        # Update step status
        photo_required = step.get('require_photo', False)
        annotations_required = step.get('require_annotations', False)
        
        status_parts = []
        if photo_required:
            status_parts.append(f"Photos: {len(self.step_images)}/1 required")
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
        
        self.step_status.setText(" | ".join(status_parts) if status_parts else "Optional documentation")
        
        # Update navigation buttons
        self.prev_button.setEnabled(self.current_step > 0)
        
        is_last_step = self.current_step == len(steps) - 1
        self.next_button.setVisible(not is_last_step)
        self.finish_button.setVisible(is_last_step)
    
    def on_checkboxes_changed(self, checked, total):
        """Handle checkbox status change."""
        self.show_current_step()  # Refresh status display
    
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
            # Check if any image has markers (non-empty list)
            has_annotations = any(img.get('markers') and len(img.get('markers', [])) > 0 
                                 for img in self.step_images)
            if not has_annotations:
                QMessageBox.warning(self, "Annotations Required", 
                                   "This step requires annotations (markers) on captured images.\n\n"
                                   "Click on the camera preview to add markers (A, B, C...) before capturing.")
                return False
        
        return True
    
    def on_back_clicked(self):
        """Handle back to menu button click."""
        # Check if user has unsaved work
        if self.captured_images:
            reply = QMessageBox.question(
                self,
                "Return to Menu?",
                f"You have {len(self.captured_images)} captured image(s) in this workflow.\n\n"
                "Are you sure you want to return to the menu without finishing?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        self.cleanup_resources()
        self.back_requested.emit()
    
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
    
    def show_reference_fullsize(self, event):
        """Show reference image in full size popup."""
        if not self.reference_image_path:
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Reference Image - Full Size")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Load and display full size image
        image_label = QLabel()
        pixmap = QPixmap(self.reference_image_path)
        
        # Scale to fit screen if too large (90% of screen size)
        screen = self.screen().geometry()
        max_width = int(screen.width() * 0.9)
        max_height = int(screen.height() * 0.9)
        
        if pixmap.width() > max_width or pixmap.height() > max_height:
            pixmap = pixmap.scaled(max_width, max_height,
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
        
        image_label.setPixmap(pixmap)
        layout.addWidget(image_label)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.exec_()
    
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
