"""Annotatable camera preview widget with draggable markers."""
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QPainterPath
import string


class AnnotatablePreview(QLabel):
    """Camera preview label with annotation markers."""
    
    markers_changed = pyqtSignal()  # Emitted when markers are added/moved
    
    def __init__(self):
        super().__init__()
        self.markers = []  # List of {pos: QPoint, label: str}
        self.dragging_marker = None
        self.drag_offset = QPoint()
        self.current_frame = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
    
    def add_marker(self, pos):
        """Add a new marker at the given position."""
        # Generate label (A, B, C, ...)
        label = string.ascii_uppercase[len(self.markers) % 26]
        if len(self.markers) >= 26:
            # After Z, use AA, AB, etc.
            label = string.ascii_uppercase[(len(self.markers) // 26) - 1] + label
        
        self.markers.append({'pos': pos, 'label': label})
        self.markers_changed.emit()
        self.update()
    
    def clear_markers(self):
        """Remove all markers."""
        self.markers = []
        self.markers_changed.emit()
        self.update()
    
    def get_markers_data(self):
        """Get marker data for saving with image."""
        return [{'x': m['pos'].x(), 'y': m['pos'].y(), 'label': m['label']} 
                for m in self.markers]
    
    def set_frame(self, pixmap):
        """Set the current camera frame."""
        self.current_frame = pixmap
        self.update()
    
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
            # Change cursor if hovering over marker
            hovering = any(self._is_near_marker(event.pos(), m['pos']) for m in self.markers)
            self.setCursor(Qt.OpenHandCursor if hovering else Qt.CrossCursor)
    
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
        super().paintEvent(event)
        
        if not self.current_frame:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw the camera frame
        painter.drawPixmap(self.rect(), self.current_frame)
        
        # Draw markers
        for marker in self.markers:
            self._draw_marker(painter, marker['pos'], marker['label'])
        
        painter.end()
    
    def _draw_marker(self, painter, pos, label):
        """Draw a single marker (arrow with label)."""
        # Arrow parameters
        arrow_length = 40
        arrow_width = 15
        
        # Draw arrow pointing down-right
        arrow_path = QPainterPath()
        arrow_path.moveTo(pos.x(), pos.y())
        arrow_path.lineTo(pos.x() + arrow_length, pos.y() + arrow_length)
        
        # Arrowhead
        arrow_path.lineTo(pos.x() + arrow_length - 10, pos.y() + arrow_length)
        arrow_path.lineTo(pos.x() + arrow_length, pos.y() + arrow_length + 10)
        arrow_path.lineTo(pos.x() + arrow_length, pos.y() + arrow_length)
        
        # Draw arrow with red color
        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)
        painter.drawPath(arrow_path)
        
        # Draw label circle at arrow tip
        label_pos = QPoint(pos.x() + arrow_length, pos.y() + arrow_length)
        
        # White circle background
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawEllipse(label_pos, 15, 15)
        
        # Draw label text
        painter.setPen(QColor(255, 0, 0))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(label_pos.x() - 6, label_pos.y() + 6, label)
