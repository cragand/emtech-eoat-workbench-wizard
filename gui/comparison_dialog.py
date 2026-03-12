"""Comparison dialogs for reference image/video vs live camera."""
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from logger_config import get_logger

logger = get_logger(__name__)


def show_reference_fullsize(screen):
    """Show reference image in full size popup with interactive checkboxes.
    
    Args:
        screen: WorkflowExecutionScreen instance
    """
    from gui.checkbox_widgets import InteractiveReferenceImage

    if not screen.reference_image_path:
        return

    dialog = QDialog(screen)
    dialog.setWindowTitle("Reference Image - Full Size")
    dialog.setModal(False)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    fullsize_ref = InteractiveReferenceImage()

    step = screen.workflow['steps'][screen.current_step]
    checkbox_data = step.get('inspection_checkboxes', [])

    current_checkboxes = [{'x': cb['x'], 'y': cb['y'], 'checked': cb['checked']}
                         for cb in screen.reference_image.checkboxes]

    fullsize_ref.set_image_and_checkboxes(screen.reference_image_path, current_checkboxes)

    scr = screen.screen().geometry()
    dialog.resize(int(scr.width() * 0.6), int(scr.height() * 0.6))

    def sync_checkboxes(checked, total):
        for i, cb in enumerate(fullsize_ref.checkboxes):
            if i < len(screen.reference_image.checkboxes):
                screen.reference_image.checkboxes[i]['checked'] = cb['checked']
        screen.reference_image.update()
        screen.reference_image.emit_status()
        screen.update_step_status()

    fullsize_ref.checkboxes_changed.connect(sync_checkboxes)
    layout.addWidget(fullsize_ref)

    close_button = QPushButton("Close")
    close_button.setMaximumHeight(35)
    close_button.setStyleSheet("""
        QPushButton {
            background-color: #77C25E; color: white; border: none;
            border-radius: 3px; padding: 8px 15px; font-weight: bold;
        }
        QPushButton:hover { background-color: #5FA84A; }
    """)
    close_button.clicked.connect(dialog.close)
    layout.addWidget(close_button)

    dialog.show()
