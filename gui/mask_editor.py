"""Mask editor for creating transparent PNG overlays from captured images."""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSlider, QComboBox, QFileDialog,
                             QMessageBox, QWidget, QSizePolicy, QButtonGroup,
                             QRadioButton, QGroupBox, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt, QPoint, QRect, QSize
from PyQt5.QtGui import (QPixmap, QPainter, QColor, QImage, QPen, QBrush,
                          QCursor)
import cv2
import numpy as np
import os
from datetime import datetime


class MaskCanvas(QWidget):
    """Canvas widget for painting transparency masks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_image = None  # Original image as numpy array (BGRA)
        self.mask = None  # Alpha mask: 255=opaque, 0=transparent
        self.display_scale = 1.0
        self.offset = QPoint(0, 0)

        # Tool settings
        self.tool = "brush"  # brush, rectangle, ellipse
        self.brush_size = 30
        self.inverse_mode = False  # False=paint transparency, True=paint opacity
        self.show_checkerboard = True

        # Interaction state
        self.painting = False
        self.erasing = False
        self.shape_start = None
        self.shape_preview = None
        self.last_paint_pos = None

        # Pan/zoom
        self.panning = False
        self.pan_start = QPoint()
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        # Undo/redo
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 30

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(400, 300)

    def load_image(self, image_path):
        """Load an image and initialize the mask."""
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return False

        # Convert to BGRA if needed
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
        elif img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

        self.source_image = img
        # Start fully opaque (user paints transparency) or fully transparent (inverse)
        if self.inverse_mode:
            self.mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
        else:
            self.mask = np.full((img.shape[0], img.shape[1]), 255, dtype=np.uint8)

        self.undo_stack.clear()
        self.redo_stack.clear()
        self._fit_to_view()
        self.update()
        return True

    def set_inverse_mode(self, inverse):
        """Switch between normal and inverse mode, resetting the mask."""
        if self.source_image is None:
            self.inverse_mode = inverse
            return
        if inverse == self.inverse_mode:
            return

        reply = QMessageBox.question(
            self, "Switch Mode",
            "Switching modes will reset the current mask. Continue?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return False

        self.inverse_mode = inverse
        if self.inverse_mode:
            self.mask = np.zeros((self.source_image.shape[0], self.source_image.shape[1]), dtype=np.uint8)
        else:
            self.mask = np.full((self.source_image.shape[0], self.source_image.shape[1]), 255, dtype=np.uint8)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.update()
        return True

    def _fit_to_view(self):
        """Fit image to widget size."""
        if self.source_image is None:
            return
        h, w = self.source_image.shape[:2]
        ww, wh = self.width(), self.height()
        self.zoom_level = min(ww / w, wh / h, 1.0)
        # Center the image
        scaled_w = w * self.zoom_level
        scaled_h = h * self.zoom_level
        self.offset = QPoint(int((ww - scaled_w) / 2), int((wh - scaled_h) / 2))

    def _push_undo(self):
        """Save current mask state for undo."""
        if self.mask is not None:
            self.undo_stack.append(self.mask.copy())
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
            self.redo_stack.clear()

    def undo(self):
        if self.undo_stack and self.mask is not None:
            self.redo_stack.append(self.mask.copy())
            self.mask = self.undo_stack.pop()
            self.update()

    def redo(self):
        if self.redo_stack and self.mask is not None:
            self.undo_stack.append(self.mask.copy())
            self.mask = self.redo_stack.pop()
            self.update()

    def _widget_to_image(self, pos):
        """Convert widget coordinates to image coordinates."""
        x = (pos.x() - self.offset.x()) / self.zoom_level
        y = (pos.y() - self.offset.y()) / self.zoom_level
        return int(x), int(y)

    def _paint_at(self, ix, iy, erase=False):
        """Paint or erase at image coordinates."""
        if self.mask is None:
            return
        h, w = self.mask.shape
        # In normal mode: painting sets alpha=0 (transparent), erasing restores alpha=255
        # In inverse mode: painting sets alpha=255 (opaque), erasing sets alpha=0
        if erase:
            value = 255 if self.inverse_mode else 255
            # Erase always restores to the mode's default
            value = 0 if self.inverse_mode else 255
        else:
            value = 255 if self.inverse_mode else 0

        cv2.circle(self.mask, (ix, iy), self.brush_size // 2, int(value), -1)

    def _paint_line(self, x1, y1, x2, y2, erase=False):
        """Paint a line between two points for smooth strokes."""
        if self.mask is None:
            return
        if erase:
            value = 0 if self.inverse_mode else 255
        else:
            value = 255 if self.inverse_mode else 0
        cv2.line(self.mask, (x1, y1), (x2, y2), int(value), self.brush_size)

    def _apply_shape(self, start, end, erase=False):
        """Apply rectangle or ellipse shape to mask."""
        if self.mask is None:
            return
        ix1, iy1 = self._widget_to_image(start)
        ix2, iy2 = self._widget_to_image(end)
        x1, x2 = min(ix1, ix2), max(ix1, ix2)
        y1, y2 = min(iy1, iy2), max(iy1, iy2)

        if erase:
            value = 0 if self.inverse_mode else 255
        else:
            value = 255 if self.inverse_mode else 0

        if self.tool == "rectangle":
            cv2.rectangle(self.mask, (x1, y1), (x2, y2), int(value), -1)
        elif self.tool == "ellipse":
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            rx, ry = (x2 - x1) // 2, (y2 - y1) // 2
            if rx > 0 and ry > 0:
                cv2.ellipse(self.mask, (cx, cy), (rx, ry), 0, 0, 360, int(value), -1)

    def paintEvent(self, event):
        """Render the canvas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Background
        painter.fillRect(self.rect(), QColor(50, 50, 50))

        if self.source_image is None:
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, "No image loaded")
            painter.end()
            return

        h, w = self.source_image.shape[:2]
        scaled_w = int(w * self.zoom_level)
        scaled_h = int(h * self.zoom_level)

        # Build display image
        display = self.source_image.copy()
        display[:, :, 3] = self.mask

        if self.show_checkerboard:
            # Create checkerboard for transparent areas
            checker = self._make_checkerboard(w, h, 16)
            # Blend: where alpha is 0, show checkerboard with source image bleed-through
            alpha = self.mask.astype(np.float32) / 255.0
            alpha3 = np.stack([alpha] * 3, axis=-1)
            rgb = display[:, :, :3].astype(np.float32)
            checker_f = checker.astype(np.float32)
            # In paint opacity mode, show more of the source through the checkerboard
            src_bleed = 0.55 if self.inverse_mode else 0.15
            checker_blend = checker_f * (1 - src_bleed) + rgb * src_bleed
            blended = (rgb * alpha3 + checker_blend * (1 - alpha3)).astype(np.uint8)
            # In paint opacity mode, draw border outline around opaque areas
            if self.inverse_mode:
                contours, _ = cv2.findContours(self.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(blended, contours, -1, (0, 200, 255), 2)
            display[:, :, :3] = blended
            display[:, :, 3] = 255  # Fully opaque for display

        # Convert to QImage - OpenCV BGRA maps to Format_ARGB32 on little-endian
        qimg = QImage(display.data, w, h, display.strides[0], QImage.Format_ARGB32)
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(scaled_w, scaled_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        painter.drawPixmap(self.offset, scaled)

        # Shape preview
        if self.shape_start and self.shape_preview and self.tool in ("rectangle", "ellipse"):
            painter.setPen(QPen(QColor(0, 150, 255), 2, Qt.DashLine))
            painter.setBrush(QColor(0, 150, 255, 40))
            rect = QRect(self.shape_start, self.shape_preview).normalized()
            if self.tool == "rectangle":
                painter.drawRect(rect)
            else:
                painter.drawEllipse(rect)

        # Brush cursor preview
        if self.tool == "brush" and self.underMouse():
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            radius = int(self.brush_size * self.zoom_level / 2)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(cursor_pos, radius, radius)

        painter.end()

    def _make_checkerboard(self, w, h, cell_size):
        """Generate a checkerboard pattern."""
        checker = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(0, h, cell_size):
            for x in range(0, w, cell_size):
                if ((x // cell_size) + (y // cell_size)) % 2 == 0:
                    checker[y:y+cell_size, x:x+cell_size] = [200, 200, 200]
                else:
                    checker[y:y+cell_size, x:x+cell_size] = [150, 150, 150]
        return checker

    def mousePressEvent(self, event):
        if self.source_image is None:
            return

        # Middle button or Ctrl+Left for panning
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier):
            self.panning = True
            self.pan_start = event.pos() - self.offset
            self.setCursor(Qt.ClosedHandCursor)
            return

        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            erase = event.button() == Qt.RightButton
            if self.tool == "brush":
                self._push_undo()
                self.painting = True
                self.erasing = erase
                ix, iy = self._widget_to_image(event.pos())
                self._paint_at(ix, iy, erase)
                self.last_paint_pos = (ix, iy)
                self.update()
            elif self.tool in ("rectangle", "ellipse"):
                self._push_undo()
                self.shape_start = event.pos()
                self.shape_preview = event.pos()
                self.erasing = erase
                self.update()

    def mouseMoveEvent(self, event):
        if self.panning:
            self.offset = event.pos() - self.pan_start
            self.update()
            return

        if self.painting and self.tool == "brush":
            ix, iy = self._widget_to_image(event.pos())
            if self.last_paint_pos:
                self._paint_line(self.last_paint_pos[0], self.last_paint_pos[1], ix, iy, self.erasing)
            else:
                self._paint_at(ix, iy, self.erasing)
            self.last_paint_pos = (ix, iy)
            self.update()
        elif self.shape_start and self.tool in ("rectangle", "ellipse"):
            self.shape_preview = event.pos()
            self.update()
        elif self.tool == "brush":
            self.update()  # Update brush cursor

    def mouseReleaseEvent(self, event):
        if self.panning:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            return

        if self.tool == "brush":
            self.painting = False
            self.last_paint_pos = None
        elif self.tool in ("rectangle", "ellipse") and self.shape_start:
            self._apply_shape(self.shape_start, event.pos(), self.erasing)
            self.shape_start = None
            self.shape_preview = None
            self.update()

    def wheelEvent(self, event):
        """Zoom with scroll wheel."""
        if self.source_image is None:
            return
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        new_zoom = self.zoom_level * factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))

        # Zoom toward cursor position
        cursor = event.pos()
        old_img_x = (cursor.x() - self.offset.x()) / self.zoom_level
        old_img_y = (cursor.y() - self.offset.y()) / self.zoom_level
        self.zoom_level = new_zoom
        new_ox = cursor.x() - old_img_x * self.zoom_level
        new_oy = cursor.y() - old_img_y * self.zoom_level
        self.offset = QPoint(int(new_ox), int(new_oy))
        self.update()

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self.undo()
                return
            elif event.key() == Qt.Key_Y:
                self.redo()
                return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.source_image is not None:
            self._fit_to_view()

    def get_result_image(self):
        """Return the final BGRA image with alpha from mask."""
        if self.source_image is None or self.mask is None:
            return None
        result = self.source_image.copy()
        result[:, :, 3] = self.mask
        return result


class MaskEditorDialog(QDialog):
    """Dialog for creating transparent PNG overlay masks from images."""

    def __init__(self, image_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Overlay Mask Editor")
        self.setMinimumSize(900, 650)
        self.saved_path = None
        self.init_ui()
        if image_path:
            self.load_image(image_path)

    def init_ui(self):
        layout = QHBoxLayout()

        # Left panel - tools
        tool_panel = QWidget()
        tool_panel.setMaximumWidth(220)
        tool_panel.setMinimumWidth(200)
        tool_layout = QVBoxLayout(tool_panel)
        tool_layout.setContentsMargins(5, 5, 5, 5)

        # Load image button
        self.load_button = QPushButton("📂 Load Image")
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; color: white; border: none;
                border-radius: 3px; font-weight: bold; padding: 8px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.load_button.clicked.connect(self.browse_image)
        tool_layout.addWidget(self.load_button)

        # Mode selection
        mode_group = QGroupBox("Paint Mode")
        mode_layout = QVBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.normal_radio = QRadioButton("Paint Transparency")
        self.normal_radio.setToolTip("Paint areas to make transparent (remove)")
        self.normal_radio.setChecked(True)
        self.inverse_radio = QRadioButton("Paint Opacity (Inverse)")
        self.inverse_radio.setToolTip("Start transparent, paint areas to keep visible")
        self.mode_group.addButton(self.normal_radio, 0)
        self.mode_group.addButton(self.inverse_radio, 1)
        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        mode_layout.addWidget(self.normal_radio)
        mode_layout.addWidget(self.inverse_radio)
        mode_group.setLayout(mode_layout)
        tool_layout.addWidget(mode_group)

        # Tool selection
        tools_group = QGroupBox("Tool")
        tools_layout = QVBoxLayout()
        self.tool_group = QButtonGroup(self)
        self.brush_radio = QRadioButton("🖌 Brush")
        self.brush_radio.setChecked(True)
        self.rect_radio = QRadioButton("▭ Rectangle")
        self.ellipse_radio = QRadioButton("⬭ Ellipse")
        self.tool_group.addButton(self.brush_radio, 0)
        self.tool_group.addButton(self.rect_radio, 1)
        self.tool_group.addButton(self.ellipse_radio, 2)
        self.tool_group.buttonClicked.connect(self._on_tool_changed)
        tools_layout.addWidget(self.brush_radio)
        tools_layout.addWidget(self.rect_radio)
        tools_layout.addWidget(self.ellipse_radio)
        tools_group.setLayout(tools_layout)
        tool_layout.addWidget(tools_group)

        # Brush size
        brush_group = QGroupBox("Brush Size")
        brush_layout = QVBoxLayout()
        self.brush_label = QLabel("30 px")
        self.brush_label.setAlignment(Qt.AlignCenter)
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(2, 200)
        self.brush_slider.setValue(30)
        self.brush_slider.valueChanged.connect(self._on_brush_changed)
        brush_layout.addWidget(self.brush_label)
        brush_layout.addWidget(self.brush_slider)
        brush_group.setLayout(brush_layout)
        tool_layout.addWidget(brush_group)

        # Preview toggle
        self.checkerboard_check = QCheckBox("Show transparency preview")
        self.checkerboard_check.setChecked(True)
        self.checkerboard_check.toggled.connect(self._on_checkerboard_toggled)
        tool_layout.addWidget(self.checkerboard_check)

        # Undo/Redo
        undo_layout = QHBoxLayout()
        self.undo_button = QPushButton("↩ Undo")
        self.undo_button.setStyleSheet("""
            QPushButton { background-color: #666; color: white; border: none;
                border-radius: 3px; padding: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #888; }
        """)
        self.undo_button.clicked.connect(lambda: self.canvas.undo())
        self.redo_button = QPushButton("↪ Redo")
        self.redo_button.setStyleSheet("""
            QPushButton { background-color: #666; color: white; border: none;
                border-radius: 3px; padding: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #888; }
        """)
        self.redo_button.clicked.connect(lambda: self.canvas.redo())
        undo_layout.addWidget(self.undo_button)
        undo_layout.addWidget(self.redo_button)
        tool_layout.addLayout(undo_layout)

        # Reset button
        self.reset_button = QPushButton("🔄 Reset Mask")
        self.reset_button.setStyleSheet("""
            QPushButton { background-color: #FF6B6B; color: white; border: none;
                border-radius: 3px; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #FF5252; }
        """)
        self.reset_button.clicked.connect(self._reset_mask)
        tool_layout.addWidget(self.reset_button)

        tool_layout.addStretch()

        # Help text
        help_label = QLabel(
            "Left-click: Paint\n"
            "Right-click: Erase\n"
            "Scroll: Zoom\n"
            "Ctrl+Drag / Middle: Pan\n"
            "Ctrl+Z / Ctrl+Y: Undo/Redo"
        )
        help_label.setStyleSheet("color: #888; font-size: 9pt; padding: 5px; "
                                 "background-color: #f0f0f0; border-radius: 3px;")
        help_label.setWordWrap(True)
        tool_layout.addWidget(help_label)

        # Save button
        self.save_button = QPushButton("💾 Save as PNG Overlay")
        self.save_button.setStyleSheet("""
            QPushButton { background-color: #77C25E; color: white; border: none;
                border-radius: 3px; font-weight: bold; padding: 10px; font-size: 11pt; }
            QPushButton:hover { background-color: #5FA84A; }
            QPushButton:disabled { background-color: #CCCCCC; color: #666; }
        """)
        self.save_button.clicked.connect(self.save_mask)
        self.save_button.setEnabled(False)
        tool_layout.addWidget(self.save_button)

        layout.addWidget(tool_panel)

        # Canvas
        self.canvas = MaskCanvas()
        layout.addWidget(self.canvas, 1)

        self.setLayout(layout)

    def load_image(self, path):
        """Load an image into the canvas."""
        if self.canvas.load_image(path):
            self.save_button.setEnabled(True)
            self.setWindowTitle(f"Overlay Mask Editor - {os.path.basename(path)}")
        else:
            QMessageBox.warning(self, "Load Error", f"Could not load image:\n{path}")

    def browse_image(self):
        """Browse for an image to load."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp);;All Files (*)")
        if file_path:
            self.load_image(file_path)

    def _on_mode_changed(self, button):
        idx = self.mode_group.id(button)
        result = self.canvas.set_inverse_mode(idx == 1)
        if result is False:
            # User cancelled — revert radio
            if idx == 1:
                self.normal_radio.setChecked(True)
            else:
                self.inverse_radio.setChecked(True)

    def _on_tool_changed(self, button):
        tools = {0: "brush", 1: "rectangle", 2: "ellipse"}
        self.canvas.tool = tools.get(self.tool_group.id(button), "brush")

    def _on_brush_changed(self, value):
        self.brush_label.setText(f"{value} px")
        self.canvas.brush_size = value

    def _on_checkerboard_toggled(self, checked):
        self.canvas.show_checkerboard = checked
        self.canvas.update()

    def _reset_mask(self):
        if self.canvas.source_image is None:
            return
        reply = QMessageBox.question(self, "Reset Mask",
                                     "Reset the mask to its initial state?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.canvas._push_undo()
            h, w = self.canvas.source_image.shape[:2]
            if self.canvas.inverse_mode:
                self.canvas.mask = np.zeros((h, w), dtype=np.uint8)
            else:
                self.canvas.mask = np.full((h, w), 255, dtype=np.uint8)
            self.canvas.update()

    def save_mask(self):
        """Save the masked image as a PNG with transparency."""
        result = self.canvas.get_result_image()
        if result is None:
            return

        # Default save location
        default_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   "resources", "overlay_masks")
        os.makedirs(default_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"overlay_mask_{timestamp}.png"
        default_path = os.path.join(default_dir, default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Overlay Mask", default_path,
            "PNG Images (*.png)")
        if not file_path:
            return

        if not file_path.lower().endswith('.png'):
            file_path += '.png'

        # Save as BGRA PNG
        cv2.imwrite(file_path, result)
        self.saved_path = file_path
        QMessageBox.information(self, "Mask Saved",
                                f"Overlay mask saved to:\n{file_path}\n\n"
                                "You can now select this file as a reference image\n"
                                "in a workflow step with the overlay option enabled.")
