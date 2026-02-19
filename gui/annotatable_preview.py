"""Annotatable camera preview widget with draggable markers."""
from PyQt5.QtWidgets import QLabel, QDialog, QVBoxLayout, QTextEdit, QPushButton, QDialogButtonBox
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QPainterPath
import string
import math


class MarkerNoteDialog(QDialog):
    """Dialog for editing marker notes."""
    
    def __init__(self, marker_label, current_note="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Marker {marker_label} - Notes")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # Explicitly apply application stylesheet to ensure theme is respected
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            self.setStyleSheet(app.styleSheet())
        
        layout = QVBoxLayout()
        
        label = QLabel(f"Notes for Marker {marker_label}:")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)
        
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Enter notes for this marker...")
        self.note_input.setText(current_note)
        self.note_input.setMaximumHeight(150)
        layout.addWidget(self.note_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        # Position dialog to the right of parent window to not obstruct camera view
        if parent:
            parent_geo = parent.window().geometry()
            # Position to the right of the parent window
            self.move(parent_geo.right() - self.width() - 20, parent_geo.top() + 100)
    
    def get_note(self):
        """Get the entered note."""
        return self.note_input.toPlainText().strip()


class AnnotatablePreview(QLabel):
    """Camera preview label with annotation markers."""
    
    markers_changed = pyqtSignal()  # Emitted when markers are added/moved
    
    def __init__(self):
        super().__init__()
        self.markers = []  # List of {pos: QPoint, label: str, angle: float, note: str}
        self.dragging_marker = None
        self.drag_offset = QPoint()
        self.current_frame = None
        self.hover_marker = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
    
    def add_marker(self, pos):
        """Add a new marker at the given position and prompt for note."""
        # Generate label (A, B, C, ...)
        label = string.ascii_uppercase[len(self.markers) % 26]
        if len(self.markers) >= 26:
            # After Z, use AA, AB, etc.
            label = string.ascii_uppercase[(len(self.markers) // 26) - 1] + label
        
        # Create marker with empty note
        new_marker = {'pos': pos, 'label': label, 'angle': 45, 'note': ''}
        self.markers.append(new_marker)
        
        # Immediately open note dialog for the new marker
        dialog = MarkerNoteDialog(label, '', self)
        if dialog.exec_() == QDialog.Accepted:
            new_marker['note'] = dialog.get_note()
        # If dialog is cancelled/closed, marker stays with empty note
        
        self.markers_changed.emit()
        self.update()
    
    def clear_markers(self):
        """Remove all markers."""
        self.markers = []
        self.hover_marker = None
        self.markers_changed.emit()
        self.update()
    
    def get_markers_data(self):
        """Get marker data for saving with image."""
        return [{'x': m['pos'].x(), 'y': m['pos'].y(), 'label': m['label'], 'angle': m['angle'], 'note': m.get('note', '')} 
                for m in self.markers]
    
    def set_frame(self, pixmap):
        """Set the current camera frame."""
        self.current_frame = pixmap
        self.update()
    
    def wheelEvent(self, event):
        """Handle mouse wheel - rotate marker."""
        if self.hover_marker:
            # Rotate by 15 degrees per wheel step
            delta = event.angleDelta().y() / 120  # Standard wheel step
            self.hover_marker['angle'] = (self.hover_marker['angle'] + delta * 15) % 360
            self.markers_changed.emit()
            self.update()
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click - edit marker note."""
        if event.button() == Qt.LeftButton:
            for marker in self.markers:
                if self._is_near_marker(event.pos(), marker['pos']):
                    # Open note dialog
                    dialog = MarkerNoteDialog(marker['label'], marker.get('note', ''), self)
                    if dialog.exec_() == QDialog.Accepted:
                        marker['note'] = dialog.get_note()
                        self.markers_changed.emit()
                        self.update()
                    return
    
    def mousePressEvent(self, event):
        """Handle mouse press - start dragging or add marker."""
        if event.button() == Qt.LeftButton:
            # Check if clicking on existing marker
            for marker in self.markers:
                if self._is_near_marker(event.pos(), marker['pos']):
                    self.dragging_marker = marker
                    self.drag_offset = marker['pos'] - event.pos()
                    self.setCursor(Qt.ClosedHandCursor)
                    return
            
            # Add new marker if not clicking on existing one
            self.add_marker(event.pos())
        elif event.button() == Qt.RightButton:
            # Right click removes nearest marker
            for i, marker in enumerate(self.markers):
                if self._is_near_marker(event.pos(), marker['pos']):
                    self.markers.pop(i)
                    self.hover_marker = None
                    self.markers_changed.emit()
                    self.update()
                    break
    
    def mouseMoveEvent(self, event):
        """Handle mouse move - drag marker or show cursor."""
        if self.dragging_marker:
            # Update marker position
            self.dragging_marker['pos'] = event.pos() + self.drag_offset
            self.markers_changed.emit()
            self.update()
        else:
            # Update hover marker for rotation
            self.hover_marker = None
            for marker in self.markers:
                if self._is_near_marker(event.pos(), marker['pos']):
                    self.hover_marker = marker
                    break
            
            # Change cursor if hovering over marker
            self.setCursor(Qt.OpenHandCursor if self.hover_marker else Qt.CrossCursor)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - stop dragging."""
        if event.button() == Qt.LeftButton and self.dragging_marker:
            self.dragging_marker = None
            self.setCursor(Qt.CrossCursor)
    
    def _is_near_marker(self, pos, marker_pos, threshold=20):
        """Check if position is near a marker."""
        dx = pos.x() - marker_pos.x()
        dy = pos.y() - marker_pos.y()
        return (dx * dx + dy * dy) < (threshold * threshold)
    
    def paintEvent(self, event):
        """Paint the camera frame and markers."""
        if not self.current_frame:
            # Only call super if no frame (to show "No camera selected" text)
            super().paintEvent(event)
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw the camera frame centered and maintaining aspect ratio
        pixmap_rect = self.current_frame.rect()
        widget_rect = self.rect()
        
        # Calculate scaled rect that maintains aspect ratio
        scaled_pixmap = self.current_frame.scaled(
            widget_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Center the pixmap
        x = (widget_rect.width() - scaled_pixmap.width()) // 2
        y = (widget_rect.height() - scaled_pixmap.height()) // 2
        
        painter.drawPixmap(x, y, scaled_pixmap)
        
        # Draw markers
        for marker in self.markers:
            self._draw_marker(painter, marker)
        
        painter.end()
    
    def _draw_marker(self, painter, marker):
        """Draw a single marker (rotatable arrow with label)."""
        pos = marker['pos']
        label = marker['label']
        angle = marker['angle']
        has_note = bool(marker.get('note', '').strip())
        
        # Arrow parameters (smaller)
        arrow_length = 30
        
        # Calculate arrow endpoint based on angle
        angle_rad = math.radians(angle)
        end_x = pos.x() + arrow_length * math.cos(angle_rad)
        end_y = pos.y() + arrow_length * math.sin(angle_rad)
        
        # Draw arrow line
        pen = QPen(QColor(255, 0, 0), 2)
        painter.setPen(pen)
        painter.drawLine(pos.x(), pos.y(), int(end_x), int(end_y))
        
        # Draw arrowhead
        arrow_size = 8
        angle1 = angle_rad + math.radians(150)
        angle2 = angle_rad - math.radians(150)
        
        arrow_p1_x = end_x + arrow_size * math.cos(angle1)
        arrow_p1_y = end_y + arrow_size * math.sin(angle1)
        arrow_p2_x = end_x + arrow_size * math.cos(angle2)
        arrow_p2_y = end_y + arrow_size * math.sin(angle2)
        
        painter.setBrush(QColor(255, 0, 0))
        arrow_path = QPainterPath()
        arrow_path.moveTo(end_x, end_y)
        arrow_path.lineTo(arrow_p1_x, arrow_p1_y)
        arrow_path.lineTo(arrow_p2_x, arrow_p2_y)
        arrow_path.closeSubpath()
        painter.drawPath(arrow_path)
        
        # Draw label circle at arrow tip
        label_pos = QPoint(int(end_x), int(end_y))
        
        # White circle background
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawEllipse(label_pos, 12, 12)
        
        # Draw label text
        painter.setPen(QColor(255, 0, 0))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(label_pos.x() - 5, label_pos.y() + 5, label)
        
        # Draw note indicator (small blue dot) if marker has notes
        if has_note:
            painter.setBrush(QColor(0, 120, 255))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(label_pos.x() + 8, label_pos.y() - 10, 6, 6)
