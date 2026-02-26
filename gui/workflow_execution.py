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


class InteractiveReferenceImage(QLabel):
    """Reference image with interactive checkboxes."""
    
    checkboxes_changed = pyqtSignal(int, int)  # checked_count, total_count
    
    def __init__(self):
        super().__init__()
        self.image_pixmap = None
        self.checkboxes = []  # List of {'x': %, 'y': %, 'checked': bool}
        self.checkbox_history = []  # Undo history
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
    
    def set_image_and_checkboxes(self, image_path, checkbox_data):
        """Load image and set up checkboxes."""
        if not image_path or not os.path.exists(image_path):
            self.image_pixmap = None
            self.checkboxes = []
            self.checkbox_history = []
            self.clear()
            self.setText("No reference image")
            self.update()
            return
        
        self.image_pixmap = QPixmap(image_path)
        self.checkboxes = [{'x': cb['x'], 'y': cb['y'], 'checked': cb.get('checked', False)} 
                          for cb in (checkbox_data or [])]
        self.checkbox_history = []
        self.setText("")  # Clear any text
        self.update()
        self.emit_status()
    
    def mousePressEvent(self, event):
        """Toggle checkbox on click."""
        if not self.image_pixmap or not self.checkboxes:
            return
        
        # Save state for undo
        self.checkbox_history.append([{'x': cb['x'], 'y': cb['y'], 'checked': cb['checked']} 
                                      for cb in self.checkboxes])
        if len(self.checkbox_history) > 20:  # Limit history
            self.checkbox_history.pop(0)
        
        # Find which checkbox was clicked (increased hit radius for larger boxes)
        click_pos = event.pos()
        for cb in self.checkboxes:
            cb_pos = self._get_checkbox_position(cb)
            if cb_pos and (cb_pos.x() - click_pos.x())**2 + (cb_pos.y() - click_pos.y())**2 < 600:
                cb['checked'] = not cb['checked']
                self.update()
                self.emit_status()
                break
    
    def undo_checkbox(self):
        """Undo last checkbox change."""
        if self.checkbox_history:
            self.checkboxes = self.checkbox_history.pop()
            self.update()
            self.emit_status()
            return True
        return False
    
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
        
        # Draw checkboxes - larger and more visible
        for cb in self.checkboxes:
            pos = self._get_checkbox_position(cb)
            if pos:
                # Draw checkbox square
                if cb['checked']:
                    painter.setPen(QPen(QColor(255, 193, 7), 4))  # Bright amber/yellow
                    painter.setBrush(QColor(255, 193, 7, 180))
                else:
                    painter.setPen(QPen(QColor(255, 193, 7), 3))  # Bright amber/yellow
                    painter.setBrush(QColor(255, 255, 255, 220))
                
                painter.drawRect(pos.x() - 16, pos.y() - 16, 32, 32)
                
                # Draw checkmark if checked
                if cb['checked']:
                    painter.setPen(QPen(QColor(0, 0, 0), 4))
                    painter.drawLine(pos.x() - 8, pos.y(), pos.x() - 3, pos.y() + 8)
                    painter.drawLine(pos.x() - 3, pos.y() + 8, pos.x() + 10, pos.y() - 8)
        
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


class CombinedReferenceImage(QLabel):
    """Reference image with both checkboxes and annotation markers."""
    
    checkboxes_changed = pyqtSignal(int, int)  # checked_count, total_count
    markers_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.image_pixmap = None
        self.checkboxes = []
        self.markers = []
        self.dragging_marker = None
        self.drag_offset = QPoint()
        self.hover_marker = None
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
    
    def set_image_and_checkboxes(self, image_path, checkbox_data):
        """Load image and set up checkboxes."""
        if not image_path or not os.path.exists(image_path):
            self.image_pixmap = None
            self.checkboxes = []
            self.markers = []
            self.clear()
            self.setText("No reference image")
            self.update()
            return
        
        self.image_pixmap = QPixmap(image_path)
        self.checkboxes = [{'x': cb['x'], 'y': cb['y'], 'checked': False} 
                          for cb in (checkbox_data or [])]
        self.markers = []
        self.setText("")
        self.update()
    
    def _pixel_to_relative(self, pixel_pos):
        """Convert pixel position to relative coordinates (0-1) based on displayed image."""
        if not self.image_pixmap:
            return None
        
        widget_rect = self.rect()
        scaled_pixmap = self.image_pixmap.scaled(
            widget_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        x_offset = (widget_rect.width() - scaled_pixmap.width()) // 2
        y_offset = (widget_rect.height() - scaled_pixmap.height()) // 2
        
        rel_x = (pixel_pos.x() - x_offset) / scaled_pixmap.width() if scaled_pixmap.width() > 0 else 0
        rel_y = (pixel_pos.y() - y_offset) / scaled_pixmap.height() if scaled_pixmap.height() > 0 else 0
        
        rel_x = max(0, min(1, rel_x))
        rel_y = max(0, min(1, rel_y))
        
        return (rel_x, rel_y)
    
    def _relative_to_pixel(self, rel_x, rel_y):
        """Convert relative coordinates (0-1) to pixel position based on displayed image."""
        if not self.image_pixmap:
            return None
        
        pixel_x = x_offset + int(rel_x * scaled_pixmap.width())
        pixel_y = y_offset + int(rel_y * scaled_pixmap.height())
        
        return QPoint(pixel_x, pixel_y)
    
    def mousePressEvent(self, event):
        """Handle clicks for both checkboxes and markers."""
        if not self.image_pixmap:
            return
        
        click_pos = event.pos()
        
        if event.button() == Qt.LeftButton:
            # Check if clicking on a marker first
            for marker in self.markers:
                marker_pixel_pos = self._relative_to_pixel(marker['x'], marker['y'])
                if marker_pixel_pos and self._is_near_marker(click_pos, marker_pixel_pos):
                    self.dragging_marker = marker
                    self.drag_offset = marker_pixel_pos - click_pos
                    self.setCursor(Qt.ClosedHandCursor)
                    return
            
            # Check if clicking on a checkbox
            for cb in self.checkboxes:
                cb_pos = self._get_checkbox_position(cb)
                if cb_pos and (cb_pos.x() - click_pos.x())**2 + (cb_pos.y() - click_pos.y())**2 < 600:
                    cb['checked'] = not cb['checked']
                    self.update()
                    self.checkboxes_changed.emit(self.get_checked_count(), self.get_total_count())
                    return
            
            # Add new marker if not clicking on anything
            self.add_marker(click_pos)
        
        elif event.button() == Qt.RightButton:
            # Right click removes nearest marker
            for i, marker in enumerate(self.markers):
                if self._is_near_marker(click_pos, marker['pos']):
                    self.markers.pop(i)
                    self.hover_marker = None
                    self.markers_changed.emit()
                    self.update()
                    break
    
    def mouseMoveEvent(self, event):
        """Handle marker dragging and hover."""
        if self.dragging_marker:
            new_pixel_pos = event.pos() + self.drag_offset
            rel_pos = self._pixel_to_relative(new_pixel_pos)
            if rel_pos:
                self.dragging_marker['x'] = rel_pos[0]
                self.dragging_marker['y'] = rel_pos[1]
                self.markers_changed.emit()
                self.update()
        else:
            # Update hover state
            old_hover = self.hover_marker
            self.hover_marker = None
            for marker in self.markers:
                marker_pixel_pos = self._relative_to_pixel(marker['x'], marker['y'])
                if marker_pixel_pos and self._is_near_marker(event.pos(), marker_pixel_pos):
                    self.hover_marker = marker
                    break
            if old_hover != self.hover_marker:
                self.update()
    
    def mouseReleaseEvent(self, event):
        """Stop dragging marker."""
        if self.dragging_marker:
            self.dragging_marker = None
            self.setCursor(Qt.CrossCursor)
    
    def mouseDoubleClickEvent(self, event):
        """Edit marker note on double-click."""
        if event.button() == Qt.LeftButton:
            for marker in self.markers:
                marker_pixel_pos = self._relative_to_pixel(marker['x'], marker['y'])
                if marker_pixel_pos and self._is_near_marker(event.pos(), marker_pixel_pos):
                    from gui.annotatable_preview import MarkerNoteDialog
                    dialog = MarkerNoteDialog(marker['label'], marker.get('note', ''), self)
                    if dialog.exec_() == QDialog.Accepted:
                        marker['note'] = dialog.get_note()
                        self.markers_changed.emit()
                        self.update()
                    return
    
    def wheelEvent(self, event):
        """Rotate marker or adjust length on scroll."""
        if self.hover_marker:
            delta = event.angleDelta().y() / 120
            
            # Shift+Scroll adjusts length, regular scroll rotates
            if event.modifiers() & Qt.ShiftModifier:
                current_length = self.hover_marker.get('length', 30)
                new_length = current_length + (delta * 5)
                self.hover_marker['length'] = max(10, min(100, new_length))
            else:
                self.hover_marker['angle'] = (self.hover_marker['angle'] + delta * 15) % 360
            
            self.markers_changed.emit()
            self.update()
    
    def add_marker(self, pos):
        """Add a new annotation marker."""
        rel_pos = self._pixel_to_relative(pos)
        if not rel_pos:
            return
        
        import string
        label = string.ascii_uppercase[len(self.markers) % 26]
        if len(self.markers) >= 26:
            label = string.ascii_uppercase[(len(self.markers) // 26) - 1] + label
        
        new_marker = {'x': rel_pos[0], 'y': rel_pos[1], 'label': label, 'angle': 45, 'length': 30, 'note': ''}
        self.markers.append(new_marker)
        
        from gui.annotatable_preview import MarkerNoteDialog
        dialog = MarkerNoteDialog(label, '', self)
        if dialog.exec_() == QDialog.Accepted:
            new_marker['note'] = dialog.get_note()
        
        self.markers_changed.emit()
        self.update()
    
    def _is_near_marker(self, pos, marker_pos, threshold=20):
        """Check if position is near a marker."""
        dx = pos.x() - marker_pos.x()
        dy = pos.y() - marker_pos.y()
        return (dx*dx + dy*dy) < (threshold*threshold)
    
    def _get_checkbox_position(self, checkbox):
        """Convert percentage position to widget pixels."""
        if not self.image_pixmap:
            return None
        
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
        """Draw image, checkboxes, and markers."""
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
                if cb['checked']:
                    painter.setPen(QPen(QColor(255, 193, 7), 4))
                    painter.setBrush(QColor(255, 193, 7, 180))
                else:
                    painter.setPen(QPen(QColor(255, 193, 7), 3))
                    painter.setBrush(QColor(255, 255, 255, 220))
                
                painter.drawRect(pos.x() - 16, pos.y() - 16, 32, 32)
                
                if cb['checked']:
                    painter.setPen(QPen(QColor(0, 0, 0), 4))
                    painter.drawLine(pos.x() - 8, pos.y(), pos.x() - 3, pos.y() + 8)
                    painter.drawLine(pos.x() - 3, pos.y() + 8, pos.x() + 10, pos.y() - 8)
        
        # Draw markers
        for marker in self.markers:
            self._draw_marker(painter, marker)
        
        painter.end()
    
    def _draw_marker(self, painter, marker):
        """Draw an annotation marker."""
        import math
        
        # Convert relative position to pixel position
        pixel_pos = self._relative_to_pixel(marker['x'], marker['y'])
        if not pixel_pos:
            return
        
        label = marker['label']
        angle = marker.get('angle', 45)
        line_length = marker.get('length', 40)
        is_hover = (marker == self.hover_marker)
        
        # Marker colors
        if is_hover:
            line_color = QColor(255, 193, 7)
            circle_color = QColor(255, 193, 7)
            text_bg = QColor(255, 193, 7)
        else:
            line_color = QColor(119, 194, 94)
            circle_color = QColor(119, 194, 94)
            text_bg = QColor(119, 194, 94)
        
        # Draw line from center
        rad = math.radians(angle)
        end_x = pixel_pos.x() + int(line_length * math.cos(rad))
        end_y = pixel_pos.y() - int(line_length * math.sin(rad))
        
        painter.setPen(QPen(line_color, 3))
        painter.drawLine(pixel_pos.x(), pixel_pos.y(), end_x, end_y)
        
        # Draw center circle
        painter.setBrush(circle_color)
        painter.drawEllipse(pixel_pos, 6, 6)
        
        # Draw label box
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        
        text_rect = painter.fontMetrics().boundingRect(label)
        text_rect.adjust(-4, -2, 4, 2)
        text_rect.moveCenter(QPoint(end_x, end_y))
        
        painter.setBrush(text_bg)
        painter.setPen(Qt.NoPen)
        painter.drawRect(text_rect)
        
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(text_rect, Qt.AlignCenter, label)
    
    def get_checked_count(self):
        """Get number of checked boxes."""
        return sum(1 for cb in self.checkboxes if cb['checked'])
    
    def get_total_count(self):
        """Get total number of checkboxes."""
        return len(self.checkboxes)


class WorkflowExecutionScreen(QWidget):
    """Execute a workflow step-by-step with camera integration."""
    
    back_requested = pyqtSignal()
    
    def __init__(self, workflow_path, serial_number, technician, description):
        super().__init__()
        self.workflow_path = workflow_path
        self.serial_number = serial_number
        self.technician = technician
        self.description = description
        self.current_step = 0
        self.workflow = None
        self.current_camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.qr_scanner = None
        self.barcode_check_timer = None
        self.captured_images = []  # All images from workflow
        self.step_images = []  # Images for current step
        self.step_barcode_scans = []  # Barcode scans for current step
        self.step_results = {}  # Track pass/fail for each step: {step_index: bool}
        self.step_checkbox_states = {}  # Track checkbox states: {step_index: [{'x', 'y', 'checked'}]}
        
        # Video recording state
        self.is_recording = False
        self.video_writer = None
        self.current_video_path = None
        self.recorded_videos = []  # List of recorded video paths
        self.recording_start_time = None
        
        # Setup output directory - sanitize serial number for filesystem
        output_serial = self._sanitize_filename(serial_number) if serial_number else "unknown"
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "output", "captured_images", output_serial)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.load_workflow()
        self.init_ui()
        self.discover_cameras()
        self.load_progress()  # Load any saved progress
        self.show_current_step()
        self.update_breadcrumb()
        
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
            
            with open(self.workflow_path, 'r') as f:
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
        left_layout.addWidget(self.instructions_text)
        
        # Reference image header with button
        ref_header_layout = QHBoxLayout()
        ref_label = QLabel("Reference Image:")
        ref_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        ref_header_layout.addWidget(ref_label)
        ref_header_layout.addStretch()
        
        self.view_fullsize_button = QPushButton("🔍 View Full Size")
        self.view_fullsize_button.setFocusPolicy(Qt.NoFocus)
        self.view_fullsize_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.view_fullsize_button.clicked.connect(self.show_reference_fullsize)
        self.view_fullsize_button.setEnabled(False)
        ref_header_layout.addWidget(self.view_fullsize_button)
        
        self.undo_checkbox_button = QPushButton("↶ Undo")
        self.undo_checkbox_button.setFocusPolicy(Qt.NoFocus)
        self.undo_checkbox_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.undo_checkbox_button.clicked.connect(self.undo_checkbox_click)
        self.undo_checkbox_button.setEnabled(False)
        ref_header_layout.addWidget(self.undo_checkbox_button)
        
        left_layout.addLayout(ref_header_layout)
        
        self.reference_image = InteractiveReferenceImage()
        self.reference_image.setMinimumSize(300, 200)
        self.reference_image.setStyleSheet("border: 2px solid #CCCCCC;")
        self.reference_image.checkboxes_changed.connect(self.on_checkboxes_changed)
        self.reference_image_path = None  # Store current reference image path
        self.reference_checkboxes = []  # Store current checkboxes
        left_layout.addWidget(self.reference_image)
        
        splitter.addWidget(left_widget)
        
        # Right side - Camera view
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Camera selection
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Camera:")
        camera_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        camera_label.setMinimumWidth(80)
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(250)
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addStretch()
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
        self.capture_button.clicked.connect(self.capture_image)
        self.capture_button.setEnabled(False)
        capture_layout.addWidget(self.capture_button)
        
        # Scan barcode button
        self.scan_button = QPushButton("Scan Barcode/QR")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setMaximumWidth(150)
        self.scan_button.clicked.connect(self.scan_barcode)
        self.scan_button.setEnabled(False)
        capture_layout.addWidget(self.scan_button)
        
        # Record button
        self.record_button = QPushButton("🔴 Start Recording")
        self.record_button.setMinimumHeight(40)
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
        
        # Compare button
        self.compare_button = QPushButton("📷 Compare with Reference")
        self.compare_button.setFocusPolicy(Qt.NoFocus)
        self.compare_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
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
        right_layout.addWidget(self.compare_button)
        
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
                    self.timer.start(30)
                    self.capture_button.setEnabled(True)
                    self.record_button.setEnabled(True)
                    logger.info("Camera opened successfully")
                    
                    # Start barcode scanner if available
                    if QR_SCANNER_AVAILABLE:
                        logger.info("Starting barcode scanner...")
                        self.qr_scanner = QRScannerThread(self.current_camera)
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
                # If recording, write frame with annotations to video
                if self.is_recording and self.video_writer:
                    # Draw markers on frame for video
                    annotated_frame = frame.copy()
                    if self.preview_label.markers:
                        annotated_frame = self._draw_markers_on_frame(annotated_frame, self.preview_label.markers)
                    self.video_writer.write(annotated_frame)
                    
                    # Update recording timer
                    if self.recording_start_time:
                        elapsed = (datetime.now() - self.recording_start_time).total_seconds()
                        minutes = int(elapsed // 60)
                        seconds = int(elapsed % 60)
                        self.recording_indicator.setText(f"🔴 REC {minutes:02d}:{seconds:02d}")
                
                # Update preview
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
        checkbox_data = step.get('inspection_checkboxes', [])
        
        # Only load if path exists and is not empty
        if ref_image_path and os.path.exists(ref_image_path):
            self.reference_image_path = ref_image_path
            self.reference_image.set_image_and_checkboxes(ref_image_path, checkbox_data)
            self.view_fullsize_button.setEnabled(True)
        else:
            # Clear reference image completely
            self.reference_image_path = None
            self.reference_image.image_pixmap = None
            self.reference_image.checkboxes = []
            self.reference_image.clear()
            self.reference_image.setText("No reference image")
            self.view_fullsize_button.setEnabled(False)
        
        # Show/hide pass/fail buttons based on step requirement
        self.pass_fail_widget.setVisible(step.get('require_pass_fail', False))
        
        # Enable/disable compare button
        self.compare_button.setEnabled(bool(self.reference_image_path and self.current_camera))
        
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
        annotations_required = step.get('require_annotations', False)
        
        status_parts = []
        if photo_required:
            status_parts.append(f"Photos: {len(self.step_images)}/1 required")
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
        # Enable/disable undo button
        self.undo_checkbox_button.setEnabled(len(self.reference_image.checkbox_history) > 0)
    
    def undo_checkbox_click(self):
        """Handle undo button click."""
        if self.reference_image.undo_checkbox():
            self.undo_checkbox_button.setEnabled(len(self.reference_image.checkbox_history) > 0)
    
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
            if i < self.current_step:
                # Past step - check if passed
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
                else:
                    status = "✓"
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
            step_btn.setEnabled(False)  # Not clickable
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
        if event.key() == Qt.Key_Space and self.capture_button.isEnabled():
            self.capture_image()
            event.accept()
        # Enter/Return: Advance to next step (only if not typing in notes)
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and not self.notes_input.hasFocus():
            if self.finish_button.isVisible():
                self.finish_workflow()
            elif self.next_button.isEnabled():
                self.next_step()
            event.accept()
        # Ctrl+Z: Undo checkbox
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.undo_checkbox_click()
            event.accept()
        else:
            super().keyPressEvent(event)
    
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
    
    def _draw_markers_on_frame(self, frame, markers):
        """Draw annotation markers on frame."""
        frame_h, frame_w = frame.shape[:2]
        
        for marker in markers:
            # Markers are now stored as relative coordinates (0-1)
            x = int(marker['x'] * frame_w)
            y = int(marker['y'] * frame_h)
            label = marker['label']
            angle = marker.get('angle', 45)
            arrow_length = marker.get('length', 30)
            
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
    
    def mark_step_result(self, passed):
        """Mark current step as pass or fail."""
        self.step_results[self.current_step] = passed
        self.update_step_status()
        
        result_text = "PASS" if passed else "FAIL"
        QMessageBox.information(self, "Step Marked", 
                               f"Step {self.current_step + 1} marked as {result_text}")
    
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
        
        # Store checkbox state for current step (including which ones were checked)
        step = self.workflow['steps'][self.current_step]
        if step.get('inspection_checkboxes'):
            # Store the actual checkbox objects with their checked states
            self.step_checkbox_states[self.current_step] = [
                {'x': cb['x'], 'y': cb['y'], 'checked': cb['checked']} 
                for cb in self.reference_image.checkboxes
            ]
        
        if self.current_step < len(self.workflow['steps']) - 1:
            self.current_step += 1
            self.step_images = []  # Clear images for new step
            self.step_barcode_scans = []  # Clear barcode scans for new step
            self.show_current_step()
    
    def next_step(self):
        """Go to next step."""
        if not self.validate_step():
            return
        
        # Store checkbox state for current step (including which ones were checked)
        step = self.workflow['steps'][self.current_step]
        if step.get('inspection_checkboxes'):
            # Store the actual checkbox objects with their checked states
            self.step_checkbox_states[self.current_step] = [
                {'x': cb['x'], 'y': cb['y'], 'checked': cb['checked']} 
                for cb in self.reference_image.checkboxes
            ]
        
        if self.current_step < len(self.workflow['steps']) - 1:
            self.current_step += 1
            self.step_images = []  # Clear images for new step
            self.save_progress()  # Auto-save progress
            self.show_current_step()
    
    def save_progress(self):
        """Save current workflow progress."""
        try:
            progress_file = os.path.join(self.output_dir, "_workflow_progress.json")
            progress_data = {
                'workflow_path': self.workflow_path,
                'current_step': self.current_step,
                'step_results': self.step_results,
                'step_checkbox_states': self.step_checkbox_states,
                'captured_images': self.captured_images,
                'recorded_videos': self.recorded_videos,
                'serial_number': self.serial_number,
                'technician': self.technician,
                'description': self.description
            }
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
            
            # Show brief save confirmation
            self.autosave_label.setText("✓ Progress saved")
            QTimer.singleShot(2000, lambda: self.autosave_label.setText(""))
        except Exception as e:
            logger.error(f"Error saving progress: {e}", exc_info=True)
    
    def load_progress(self):
        """Load saved workflow progress if exists."""
        progress_file = os.path.join(self.output_dir, "_workflow_progress.json")
        
        try:
            if not os.path.exists(progress_file):
                return
            
            # Check if progress file is older than 30 days
            file_age_days = (datetime.now().timestamp() - os.path.getmtime(progress_file)) / 86400
            if file_age_days > 30:
                logger.info(f"Progress file is {file_age_days:.1f} days old, removing")
                os.remove(progress_file)
                return
            
            logger.info(f"Found progress file: {progress_file}")
            
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            
            # Validate progress data structure
            if not isinstance(progress_data, dict):
                raise ValueError("Progress file is not a valid JSON object")
            
            # Verify it's the same workflow
            if progress_data.get('workflow_path') != self.workflow_path:
                logger.warning("Progress file is for a different workflow, ignoring")
                return
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Resume Progress?")
            msg.setText(f"Found saved progress at step {progress_data.get('current_step', 0) + 1}.")
            msg.setInformativeText("What would you like to do?")
            
            resume_btn = msg.addButton("Resume", QMessageBox.AcceptRole)
            report_btn = msg.addButton("Generate Partial Report", QMessageBox.ActionRole)
            back_btn = msg.addButton("Back to Menu", QMessageBox.RejectRole)
            
            msg.exec_()
            
            if msg.clickedButton() == resume_btn:
                # Resume progress
                logger.info("Resuming workflow progress")
                self.current_step = progress_data.get('current_step', 0)
                self.step_results = progress_data.get('step_results', {})
                self.step_results = {int(k): v for k, v in self.step_results.items()}
                self.step_checkbox_states = progress_data.get('step_checkbox_states', {})
                self.step_checkbox_states = {int(k): v for k, v in self.step_checkbox_states.items()}
                self.captured_images = progress_data.get('captured_images', [])
                self.recorded_videos = progress_data.get('recorded_videos', [])
            elif msg.clickedButton() == report_btn:
                # Generate partial report
                logger.info("Generating partial report from progress")
                self.step_results = progress_data.get('step_results', {})
                self.step_results = {int(k): v for k, v in self.step_results.items()}
                self.step_checkbox_states = progress_data.get('step_checkbox_states', {})
                self.step_checkbox_states = {int(k): v for k, v in self.step_checkbox_states.items()}
                self.captured_images = progress_data.get('captured_images', [])
                self.recorded_videos = progress_data.get('recorded_videos', [])
                
                # Generate report with partial data
                self.generate_workflow_report()
                
                # Delete progress and exit
                os.remove(progress_file)
                QMessageBox.information(self, "Partial Report Generated", 
                                      "Partial report has been generated.\n\nReturning to menu...")
                self.cleanup_resources()
                self.back_requested.emit()
                return
            else:
                # Back - return to menu without discarding progress
                logger.info("User chose to go back, keeping progress file")
                self.cleanup_resources()
                self.back_requested.emit()
                return
                
        except json.JSONDecodeError as e:
            logger.error(f"Progress file is corrupted (invalid JSON): {e}")
            QMessageBox.warning(self, "Corrupted Progress File",
                              "The saved progress file is corrupted and cannot be loaded.\n\n"
                              "Starting workflow from the beginning.")
            # Try to remove corrupted file
            try:
                os.remove(progress_file)
            except:
                pass
        except Exception as e:
            logger.error(f"Error loading progress: {e}", exc_info=True)
            QMessageBox.warning(self, "Progress Load Error",
                              f"Failed to load saved progress:\n{str(e)}\n\n"
                              "Starting workflow from the beginning.")
            # Try to remove problematic file
            try:
                os.remove(progress_file)
            except:
                pass
    
    def clear_progress(self):
        """Clear saved progress file."""
        try:
            progress_file = os.path.join(self.output_dir, "_workflow_progress.json")
            if os.path.exists(progress_file):
                os.remove(progress_file)
                logger.info("Progress file cleared")
        except Exception as e:
            logger.error(f"Error clearing progress: {e}", exc_info=True)
    
    def validate_step(self):
        """Validate current step requirements."""
        step = self.workflow['steps'][self.current_step]
        
        if step.get('require_photo', False) and len(self.step_images) == 0:
            QMessageBox.warning(self, "Photo Required", 
                               "This step requires at least one photo before proceeding.")
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
        
        self.clear_progress()  # Clear saved progress
        self.cleanup_resources()
        self.back_requested.emit()
    
    def _generate_checkbox_image(self, ref_image_path, checkboxes, step_index):
        """Generate an image showing the reference with checkbox completion status.
        
        Args:
            ref_image_path: Path to reference image
            checkboxes: List of checkbox data with x, y percentages and checked status
            step_index: Step number for filename
            
        Returns:
            Path to generated checkbox image
        """
        if not os.path.exists(ref_image_path):
            return None
        
        try:
            # Load reference image
            img = cv2.imread(ref_image_path)
            if img is None:
                return None
            
            h, w = img.shape[:2]
            
            # Draw checkboxes on image
            for cb in checkboxes:
                x = int(cb['x'] * w)
                y = int(cb['y'] * h)
                is_checked = cb.get('checked', False)
                
                # Use bright amber/yellow for visibility
                if is_checked:
                    color = (7, 193, 255)  # BGR format of #FFC107 (amber)
                    fill_alpha = 0.7
                    checkmark_color = (0, 0, 0)  # Black checkmark
                else:
                    color = (7, 193, 255)  # BGR format of #FFC107 (amber)
                    fill_alpha = 0.4
                    checkmark_color = None
                
                # Draw checkbox square - larger
                cv2.rectangle(img, (x-16, y-16), (x+16, y+16), color, 3)
                
                # Fill with semi-transparent color
                overlay = img.copy()
                cv2.rectangle(overlay, (x-16, y-16), (x+16, y+16), color, -1)
                cv2.addWeighted(overlay, fill_alpha, img, 1-fill_alpha, 0, img)
                
                # Draw checkmark if checked
                if is_checked:
                    cv2.line(img, (x-8, y), (x-3, y+8), checkmark_color, 3)
                    cv2.line(img, (x-3, y+8), (x+10, y-8), checkmark_color, 3)
            
            # Save to output directory
            serial_prefix = self.serial_number if self.serial_number else "unknown"
            filename = f"{serial_prefix}_step{step_index+1}_checkboxes.jpg"
            output_path = os.path.join(self.output_dir, filename)
            cv2.imwrite(output_path, img)
            
            return output_path
            
        except Exception as e:
            print(f"Error generating checkbox image: {e}")
            return None
    
    def generate_workflow_report(self):
        """Generate PDF report for completed workflow."""
        try:
            # Store final step's checkbox state
            step = self.workflow['steps'][self.current_step]
            if step.get('inspection_checkboxes'):
                self.step_checkbox_states[self.current_step] = [
                    {'x': cb['x'], 'y': cb['y'], 'checked': cb['checked']} 
                    for cb in self.reference_image.checkboxes
                ]
            
            # Determine mode name for report
            workflow_name = self.workflow.get('name', 'Workflow')
            
            # Create checklist from steps with descriptions and checkbox images
            checklist_data = []
            for i, step in enumerate(self.workflow['steps']):
                step_title = step.get('title', f'Step {i+1}')
                step_description = step.get('instructions', '')
                has_pass_fail = step.get('require_pass_fail', False) or bool(step.get('inspection_checkboxes'))
                
                # Determine pass/fail status
                if i in self.step_results:
                    # User explicitly marked pass/fail (takes priority)
                    passed = self.step_results[i]
                else:
                    # Default to pass
                    passed = True
                    
                    # Check checkboxes (background criteria - always applies)
                    if i in self.step_checkbox_states:
                        checkbox_states = self.step_checkbox_states[i]
                        if isinstance(checkbox_states, list):
                            checked_count = sum(1 for cb in checkbox_states if cb.get('checked', False))
                            # Fail if not all checkboxes checked
                            if checked_count < len(checkbox_states):
                                passed = False
                
                # Generate checkbox completion image if checkboxes exist
                checkbox_image = None
                if step.get('reference_image') and os.path.exists(step.get('reference_image', '')):
                    # Use stored checkbox states if available, otherwise use template
                    if i in self.step_checkbox_states:
                        checkbox_states = self.step_checkbox_states[i]
                    else:
                        # No stored state - use unchecked template
                        checkbox_states = [{'x': cb['x'], 'y': cb['y'], 'checked': False} 
                                         for cb in step.get('inspection_checkboxes', [])]
                    
                    if checkbox_states:
                        checkbox_image = self._generate_checkbox_image(
                            step.get('reference_image'),
                            checkbox_states,
                            i
                        )
                
                checklist_data.append({
                    'name': step_title,
                    'description': step_description,
                    'passed': passed,
                    'has_pass_fail': has_pass_fail,
                    'checkbox_image': checkbox_image,
                    'step_number': i + 1
                })
            
            # Collect all barcode scans from images
            all_barcode_scans = []
            for img in self.captured_images:
                if 'barcode_scans' in img:
                    all_barcode_scans.extend(img['barcode_scans'])
            
            # Generate both PDF and DOCX reports
            pdf_path, docx_path = generate_reports(
                serial_number=self.serial_number,
                technician=self.technician,
                description=self.description,
                images=self.captured_images,
                mode_name=workflow_name,
                workflow_name=workflow_name,
                checklist_data=checklist_data,
                video_paths=self.recorded_videos,
                barcode_scans=all_barcode_scans if all_barcode_scans else None
            )
            
            video_info = f"\nVideos: {len(self.recorded_videos)}" if self.recorded_videos else ""
            QMessageBox.information(self, "Reports Generated", 
                                   f"PDF and DOCX reports generated successfully!\n\n"
                                   f"PDF: {pdf_path}\n\n"
                                   f"DOCX: {docx_path}\n\n"
                                   f"Images: {len(self.captured_images)}\n"
                                   f"Steps completed: {len(checklist_data)}{video_info}")
        
        except Exception as e:
            QMessageBox.critical(self, "Report Error", 
                               f"Failed to generate report:\n{str(e)}")
    
    def show_reference_fullsize(self):
        """Show reference image in full size popup with interactive checkboxes."""
        if not self.reference_image_path:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Reference Image - Full Size")
        dialog.setModal(False)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Create interactive reference image for dialog
        fullsize_ref = InteractiveReferenceImage()
        
        # Get current step's checkbox data
        step = self.workflow['steps'][self.current_step]
        checkbox_data = step.get('inspection_checkboxes', [])
        
        # Copy current checkbox states from main reference image
        current_checkboxes = [{'x': cb['x'], 'y': cb['y'], 'checked': cb['checked']} 
                             for cb in self.reference_image.checkboxes]
        
        # Load image with current checkbox states
        fullsize_ref.set_image_and_checkboxes(self.reference_image_path, current_checkboxes)
        
        # Set reasonable initial size (60% of screen)
        screen = self.screen().geometry()
        initial_width = int(screen.width() * 0.6)
        initial_height = int(screen.height() * 0.6)
        dialog.resize(initial_width, initial_height)
        
        # Sync checkbox changes back to main reference image
        def sync_checkboxes(checked, total):
            # Copy checkbox states back to main view
            for i, cb in enumerate(fullsize_ref.checkboxes):
                if i < len(self.reference_image.checkboxes):
                    self.reference_image.checkboxes[i]['checked'] = cb['checked']
            self.reference_image.update()
            self.reference_image.emit_status()
            self.update_step_status()
        
        fullsize_ref.checkboxes_changed.connect(sync_checkboxes)
        
        layout.addWidget(fullsize_ref)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.setMaximumHeight(35)
        close_button.setStyleSheet("""
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
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.show()
    
    def show_comparison(self):
        """Show side-by-side comparison of reference and live camera."""
        if not self.reference_image_path or not self.current_camera:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Reference vs Live Camera Comparison")
        dialog.setModal(False)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Compact header with labels
        header_layout = QHBoxLayout()
        ref_label = QLabel("Reference Image")
        ref_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        ref_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(ref_label)
        
        live_label = QLabel("Live Camera")
        live_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        live_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(live_label)
        
        layout.addLayout(header_layout)
        
        # Split view for images
        from PyQt5.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Reference image with checkboxes and markers
        ref_display = CombinedReferenceImage()
        ref_display.setStyleSheet("border: 2px solid #77C25E; background-color: #2b2b2b;")
        ref_display.setMinimumSize(400, 300)
        
        # Load reference image with checkboxes - copy current state from main view
        checkbox_data = []
        if hasattr(self, 'workflow') and self.workflow:
            current_step = self.workflow['steps'][self.current_step]
            checkbox_data = current_step.get('inspection_checkboxes', [])
        ref_display.set_image_and_checkboxes(self.reference_image_path, checkbox_data)
        
        # Copy current checkbox states from main view
        if hasattr(self.reference_image, 'checkboxes'):
            for i, cb in enumerate(self.reference_image.checkboxes):
                if i < len(ref_display.checkboxes):
                    ref_display.checkboxes[i]['checked'] = cb['checked']
            ref_display.update()
        
        # Sync checkboxes back to main view when changed
        def sync_checkboxes():
            if hasattr(self.reference_image, 'checkboxes'):
                for i, cb in enumerate(ref_display.checkboxes):
                    if i < len(self.reference_image.checkboxes):
                        self.reference_image.checkboxes[i]['checked'] = cb['checked']
                self.reference_image.update()
                self.reference_image.emit_status()
                self.update_step_status()
        
        ref_display.checkboxes_changed.connect(sync_checkboxes)
        
        splitter.addWidget(ref_display)
        
        # Right side: Live camera with annotations and action buttons
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Live camera preview
        live_display = AnnotatablePreview()
        live_display.setStyleSheet("border: 2px solid #2196F3; background-color: #2b2b2b;")
        live_display.setMinimumSize(400, 300)
        
        # Copy current markers from main preview
        if hasattr(self.preview_label, 'markers'):
            live_display.markers = [m.copy() for m in self.preview_label.markers]
            live_display.update()
        
        # Sync markers back to main preview when changed
        def sync_markers():
            if hasattr(self.preview_label, 'markers'):
                self.preview_label.markers = [m.copy() for m in live_display.markers]
                self.preview_label.update()
        
        live_display.markers_changed.connect(sync_markers)
        
        right_layout.addWidget(live_display, 1)
        
        # Action buttons for live camera
        action_layout = QHBoxLayout()
        
        # Capture button
        capture_btn = QPushButton("📷 Capture Image")
        capture_btn.setMinimumHeight(35)
        capture_btn.setStyleSheet("""
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
        
        def capture_from_comparison():
            """Capture image from comparison view."""
            if self.current_camera:
                frame = self.current_camera.capture_frame()
                if frame is not None:
                    # Draw markers on frame
                    if live_display.markers:
                        frame = self._draw_markers_on_frame(frame, live_display.markers)
                    
                    # Save image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    camera_name = self.current_camera.name.replace(" ", "_")
                    filename = f"step{self.current_step + 1}_{camera_name}_{timestamp}.jpg"
                    filepath = os.path.join(self.output_dir, filename)
                    cv2.imwrite(filepath, frame)
                    
                    # Store image data
                    image_data = {
                        'path': filepath,
                        'camera': self.current_camera.name,
                        'notes': '',
                        'markers': live_display.get_markers_data(),
                        'step': self.current_step + 1
                    }
                    
                    self.captured_images.append(image_data)
                    self.step_images.append(image_data)
                    
                    # Clear markers after capture (consistent with main view behavior)
                    live_display.clear_markers()
                    
                    # Sync cleared markers back to main view
                    if hasattr(self.preview_label, 'markers'):
                        self.preview_label.markers = []
                        self.preview_label.update()
                    
                    self.update_step_status()
                    
                    QMessageBox.information(dialog, "Image Captured", 
                                          f"Image saved for step {self.current_step + 1}")
        
        capture_btn.clicked.connect(capture_from_comparison)
        action_layout.addWidget(capture_btn)
        
        # Record button
        record_btn = QPushButton("🔴 Start Recording")
        record_btn.setMinimumHeight(35)
        comparison_recording = {'active': False, 'writer': None, 'path': None, 'start_time': None}
        
        def toggle_comparison_recording():
            """Toggle video recording in comparison view."""
            try:
                if not comparison_recording['active']:
                    # Start recording
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    video_filename = f"video_{timestamp}.mp4"
                    video_path = os.path.join(self.output_dir, video_filename)
                    
                    frame = self.current_camera.capture_frame()
                    if frame is None:
                        raise Exception("Cannot start recording: no frame available")
                    
                    h, w = frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    writer = cv2.VideoWriter(video_path, fourcc, 30.0, (w, h))
                    
                    if not writer.isOpened():
                        raise Exception("Failed to initialize video writer")
                    
                    comparison_recording['active'] = True
                    comparison_recording['writer'] = writer
                    comparison_recording['path'] = video_path
                    comparison_recording['start_time'] = datetime.now()
                    
                    record_btn.setText("⏹ Stop Recording")
                    record_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #28A745;
                            color: white;
                            border: none;
                            border-radius: 3px;
                            padding: 8px 15px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #218838;
                        }
                    """)
                    logger.info(f"Started recording in comparison view: {video_path}")
                else:
                    # Stop recording
                    if comparison_recording['writer']:
                        comparison_recording['writer'].release()
                    
                    comparison_recording['active'] = False
                    record_btn.setText("🔴 Start Recording")
                    record_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #DC3545;
                            color: white;
                            border: none;
                            border-radius: 3px;
                            padding: 8px 15px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #C82333;
                        }
                    """)
                    
                    if comparison_recording['path'] and os.path.exists(comparison_recording['path']):
                        self.recorded_videos.append(comparison_recording['path'])
                        logger.info(f"Stopped recording in comparison view: {comparison_recording['path']}")
                        QMessageBox.information(dialog, "Recording Stopped", 
                                              f"Video saved:\n{os.path.basename(comparison_recording['path'])}")
                    
                    comparison_recording['writer'] = None
                    comparison_recording['path'] = None
                    comparison_recording['start_time'] = None
                    
            except Exception as e:
                logger.error(f"Comparison recording error: {e}", exc_info=True)
                QMessageBox.warning(dialog, "Recording Error", f"Failed to record video:\n{str(e)}")
                comparison_recording['active'] = False
                if comparison_recording['writer']:
                    comparison_recording['writer'].release()
        
        record_btn.clicked.connect(toggle_comparison_recording)
        action_layout.addWidget(record_btn)
        
        right_layout.addLayout(action_layout)
        
        # Add right container to splitter
        splitter.addWidget(right_container)
        
        layout.addWidget(splitter, 1)
        
        # Update timer for live feed
        def update_comparison():
            if self.current_camera:
                frame = self.current_camera.capture_frame()
                if frame is not None:
                    # If recording in comparison view, write frame with annotations
                    if comparison_recording['active'] and comparison_recording['writer']:
                        annotated_frame = frame.copy()
                        if live_display.markers:
                            annotated_frame = self._draw_markers_on_frame(annotated_frame, live_display.markers)
                        comparison_recording['writer'].write(annotated_frame)
                    
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    live_pixmap = QPixmap.fromImage(qt_image)
                    live_display.set_frame(live_pixmap)
        
        comparison_timer = QTimer()
        comparison_timer.timeout.connect(update_comparison)
        comparison_timer.start(100)  # Update every 100ms
        # Close button - compact
        close_button = QPushButton("Close")
        close_button.setMaximumHeight(30)
        close_button.setFocusPolicy(Qt.NoFocus)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
        """)
        
        def close_dialog():
            # Stop any active recording
            if comparison_recording['active'] and comparison_recording['writer']:
                comparison_recording['writer'].release()
                if comparison_recording['path'] and os.path.exists(comparison_recording['path']):
                    self.recorded_videos.append(comparison_recording['path'])
                    logger.info(f"Auto-saved recording on dialog close: {comparison_recording['path']}")
            
            comparison_timer.stop()
            dialog.close()
        
        close_button.clicked.connect(close_dialog)
        
        # Stop timer and recording when dialog is destroyed
        def cleanup_comparison():
            comparison_timer.stop()
            if comparison_recording['active'] and comparison_recording['writer']:
                comparison_recording['writer'].release()
        
        dialog.destroyed.connect(cleanup_comparison)
        
        layout.addWidget(close_button)
        
        # Set initial size based on actual image dimensions
        ref_pixmap = QPixmap(self.reference_image_path)
        if not ref_pixmap.isNull():
            # Calculate dialog size based on image aspect ratio
            img_width = ref_pixmap.width()
            img_height = ref_pixmap.height()
            
            # Target width for each panel (2 panels side by side)
            screen = self.screen().geometry()
            max_width = int(screen.width() * 0.9)
            max_height = int(screen.height() * 0.8)
            
            # Calculate size to fit both images side by side
            panel_width = min(img_width, max_width // 2 - 50)
            panel_height = min(img_height, max_height - 100)
            
            dialog.resize(panel_width * 2 + 100, panel_height + 100)
        else:
            # Fallback to percentage-based sizing
            screen = self.screen().geometry()
            dialog.resize(int(screen.width() * 0.7), int(screen.height() * 0.6))
        
        dialog.show()
    
    def cleanup_resources(self):
        """Clean up camera resources."""
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
