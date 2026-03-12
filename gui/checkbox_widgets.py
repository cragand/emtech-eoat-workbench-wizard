"""Interactive reference image widgets with checkboxes and annotation markers."""
import math
import os
from PyQt5.QtWidgets import QLabel, QDialog
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QPixmap, QFont, QPainter, QColor, QPen


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
        
        widget_rect = self.rect()
        scaled_pixmap = self.image_pixmap.scaled(
            widget_rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        
        x_offset = (widget_rect.width() - scaled_pixmap.width()) // 2
        y_offset = (widget_rect.height() - scaled_pixmap.height()) // 2
        
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
        """Add a new annotation marker with R prefix for reference images."""
        rel_pos = self._pixel_to_relative(pos)
        if not rel_pos:
            return
        
        # Use R1, R2, R3... for reference image markers
        label = f"R{len(self.markers) + 1}"
        
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
