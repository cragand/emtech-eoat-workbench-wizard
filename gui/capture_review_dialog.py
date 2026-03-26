"""Post-capture review dialog for annotating and adding notes to a captured image."""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QFont
import cv2
import numpy as np

from gui.annotatable_preview import AnnotatablePreview
from logger_config import get_logger

logger = get_logger(__name__)


class CaptureReviewDialog(QDialog):
    """Modal dialog for reviewing a captured image, placing markers, and adding notes.

    Returns accepted/rejected.  After accept, call ``get_results()`` to retrieve
    the marker list and notes string.
    """

    def __init__(self, frame, marker_color=None, existing_markers=None,
                 existing_notes="", parent=None):
        """
        Args:
            frame: numpy BGR image (the raw captured frame, before markers are drawn).
            marker_color: QColor for annotation arrows (optional).
            existing_markers: list of marker dicts from the live preview (optional).
            existing_notes: pre-filled notes text (optional).
        """
        super().__init__(parent)
        self.setWindowTitle("Review Capture")
        self.setMinimumSize(800, 600)
        self.resize(1024, 720)

        # Store raw frame for later retrieval
        self._frame = frame.copy()

        # Convert BGR frame to QPixmap for display
        h, w = frame.shape[:2]
        if len(frame.shape) == 3:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        else:
            qimg = QImage(frame.data, w, h, w, QImage.Format_Grayscale8)
        self._pixmap = QPixmap.fromImage(qimg)

        self._build_ui(marker_color, existing_markers, existing_notes)

    # ---- UI ----

    def _build_ui(self, marker_color, existing_markers, existing_notes):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Help text
        help_text = QLabel(
            "Click: Add marker  |  Drag: Move  |  Scroll: Rotate  "
            "|  Shift+Scroll: Arrow length  |  Right-click: Remove  "
            "|  Space/Enter: Save & Close  |  Escape: Discard  "
            "|  Click image to deselect notes field"
        )
        help_text.setStyleSheet("color: #888888; font-size: 10px;")
        help_text.setAlignment(Qt.AlignCenter)
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Annotatable preview showing the frozen captured image
        self.preview = AnnotatablePreview()
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview.setFocusPolicy(Qt.ClickFocus)
        if marker_color:
            self.preview.marker_color = marker_color
        self.preview.set_frame(self._pixmap)

        # Carry over any markers placed on the live preview
        if existing_markers:
            for m in existing_markers:
                self.preview.markers.append(dict(m))
            self.preview.update()

        layout.addWidget(self.preview, 1)

        # Notes row
        notes_row = QHBoxLayout()
        notes_label = QLabel("Notes:")
        notes_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        notes_row.addWidget(notes_label)
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Add notes for this image... (Enter to save)")
        self.notes_input.setText(existing_notes)
        self.notes_input.returnPressed.connect(self.accept)
        notes_row.addWidget(self.notes_input)
        layout.addLayout(notes_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        discard_btn = QPushButton("Discard (Esc)")
        discard_btn.setFocusPolicy(Qt.NoFocus)
        discard_btn.setStyleSheet(
            "QPushButton { background-color: #888; color: white; border: none; "
            "border-radius: 3px; padding: 8px 18px; font-weight: bold; }"
            "QPushButton:hover { background-color: #666; }"
        )
        discard_btn.clicked.connect(self.reject)
        btn_row.addWidget(discard_btn)

        save_btn = QPushButton("Save (Space / Enter)")
        save_btn.setFocusPolicy(Qt.NoFocus)
        save_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; border: none; "
            "border-radius: 3px; padding: 8px 18px; font-weight: bold; }"
            "QPushButton:hover { background-color: #388E3C; }"
        )
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    # ---- Results ----

    def get_results(self):
        """Return (markers_list, notes_string) after dialog is accepted."""
        return self.preview.get_markers_data(), self.notes_input.text().strip()

    def get_frame(self):
        """Return the raw BGR frame (without markers drawn)."""
        return self._frame

    # ---- Key handling ----

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not self.notes_input.hasFocus():
            self.accept()
            event.accept()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and not self.notes_input.hasFocus():
            self.accept()
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.reject()
            event.accept()
        else:
            super().keyPressEvent(event)
