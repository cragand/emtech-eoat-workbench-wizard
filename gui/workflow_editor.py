"""Workflow editor for creating and modifying QC and maintenance workflows."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QMessageBox, QLineEdit, 
                             QTextEdit, QCheckBox, QFileDialog, QDialog, QDialogButtonBox,
                             QScrollArea, QGroupBox, QSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QPen
import os
import json
import zipfile
import shutil
import platform
import subprocess
from datetime import datetime
from reports.workflow_instructions_generator import generate_workflow_instructions as _generate_instructions


class CheckboxPlacementWidget(QLabel):
    """Widget for placing checkboxes on reference image."""
    
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.checkboxes = []  # List of QPoint positions
        self.load_image()
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
    
    def load_image(self):
        """Load and display the reference image."""
        pixmap = QPixmap(self.image_path)
        if not pixmap.isNull():
            # Scale to reasonable size for editing
            scaled = pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)
            self.setFixedSize(scaled.size())
    
    def mousePressEvent(self, event):
        """Add checkbox on left click, remove on right click."""
        if event.button() == Qt.LeftButton:
            # Add checkbox
            self.checkboxes.append(event.pos())
            self.update()
        elif event.button() == Qt.RightButton:
            # Remove nearest checkbox
            if self.checkboxes:
                pos = event.pos()
                nearest = min(self.checkboxes, 
                            key=lambda p: (p.x() - pos.x())**2 + (p.y() - pos.y())**2)
                if (nearest.x() - pos.x())**2 + (nearest.y() - pos.y())**2 < 400:  # Within 20px
                    self.checkboxes.remove(nearest)
                    self.update()
    
    def paintEvent(self, event):
        """Draw image and checkboxes."""
        super().paintEvent(event)
        
        if not self.checkboxes:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw checkboxes
        for pos in self.checkboxes:
            # Draw checkbox square
            painter.setPen(QPen(QColor(119, 194, 94), 2))  # Emtech green
            painter.setBrush(QColor(255, 255, 255, 200))
            painter.drawRect(pos.x() - 10, pos.y() - 10, 20, 20)
        
        painter.end()
    
    def get_checkboxes_data(self):
        """Get checkbox positions as percentages of image size."""
        if not self.pixmap():
            return []
        
        width = self.pixmap().width()
        height = self.pixmap().height()
        
        return [{'x': pos.x() / width, 'y': pos.y() / height} 
                for pos in self.checkboxes]
    
    def set_checkboxes_data(self, data):
        """Set checkbox positions from percentage data."""
        if not self.pixmap() or not data:
            return
        
        width = self.pixmap().width()
        height = self.pixmap().height()
        
        self.checkboxes = [QPoint(int(cb['x'] * width), int(cb['y'] * height)) 
                          for cb in data]
        self.update()


class CheckboxPlacementDialog(QDialog):
    """Dialog for placing checkboxes on reference image."""
    
    def __init__(self, image_path, existing_checkboxes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Place Inspection Checkboxes")
        self.image_path = image_path
        self.existing_checkboxes = existing_checkboxes or []
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Click on the image to place inspection checkboxes.\n"
            "Right-click near a checkbox to remove it.\n"
            "Users will check these off during workflow execution."
        )
        instructions.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 3px;")
        layout.addWidget(instructions)
        
        # Scrollable image area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.checkbox_widget = CheckboxPlacementWidget(self.image_path)
        self.checkbox_widget.set_checkboxes_data(self.existing_checkboxes)
        scroll.setWidget(self.checkbox_widget)
        layout.addWidget(scroll)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self.resize(900, 700)
    
    def get_checkboxes(self):
        """Get the placed checkboxes."""
        return self.checkbox_widget.get_checkboxes_data()



class StepEditorDialog(QDialog):
    """Dialog for editing a single workflow step."""
    
    def __init__(self, step_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Step")
        self.setMinimumSize(600, 500)
        self.step_data = step_data or {}
        
        self.init_ui()
        self.load_step_data()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        
        # Title
        title_layout = QHBoxLayout()
        title_label = QLabel("Step Title:")
        title_label.setStyleSheet("font-weight: bold;")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g., Visual Inspection")
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        # Instructions
        inst_label = QLabel("Instructions:")
        inst_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(inst_label)
        
        self.instructions_input = QTextEdit()
        self.instructions_input.setPlaceholderText("Enter detailed instructions for this step...")
        self.instructions_input.setMaximumHeight(150)
        layout.addWidget(self.instructions_input)
        
        # Reference image
        ref_layout = QHBoxLayout()
        ref_label = QLabel("Reference Image:")
        ref_label.setStyleSheet("font-weight: bold;")
        self.ref_image_input = QLineEdit()
        self.ref_image_input.setPlaceholderText("Path to reference image (optional)")
        self.ref_image_button = QPushButton("Browse...")
        self.ref_image_button.clicked.connect(self.browse_reference_image)
        ref_layout.addWidget(ref_label)
        ref_layout.addWidget(self.ref_image_input)
        ref_layout.addWidget(self.ref_image_button)
        layout.addLayout(ref_layout)
        
        # Reference image portability note
        ref_note = QLabel(
            "💡 For portability across machines:\n"
            "1. Place images in resources/qc_reference_images/ or resources/maintenance_reference_images/\n"
            "2. Use relative paths (e.g., resources/qc_reference_images/image.jpg)\n"
            "3. Commit reference images to git: git add resources/"
        )
        ref_note.setStyleSheet("color: #666666; font-size: 9pt; padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        ref_note.setWordWrap(True)
        layout.addWidget(ref_note)
        
        # Reference video
        ref_video_layout = QHBoxLayout()
        ref_video_label = QLabel("Reference Video:")
        ref_video_label.setStyleSheet("font-weight: bold;")
        self.ref_video_input = QLineEdit()
        self.ref_video_input.setPlaceholderText("Path to reference video (optional)")
        self.ref_video_button = QPushButton("Browse...")
        self.ref_video_button.clicked.connect(self.browse_reference_video)
        ref_video_layout.addWidget(ref_video_label)
        ref_video_layout.addWidget(self.ref_video_input)
        ref_video_layout.addWidget(self.ref_video_button)
        layout.addLayout(ref_video_layout)
        
        # Checkbox placement button
        self.place_checkboxes_button = QPushButton("📍 Place Inspection Checkboxes")
        self.place_checkboxes_button.setToolTip("Add checkboxes on reference image for inspection points")
        self.place_checkboxes_button.clicked.connect(self.place_checkboxes)
        self.place_checkboxes_button.setEnabled(False)
        self.ref_image_input.textChanged.connect(self.update_checkbox_button)
        layout.addWidget(self.place_checkboxes_button)
        
        # Mask editor button
        self.create_mask_button = QPushButton("🎭 Create Overlay Mask from Image")
        self.create_mask_button.setToolTip("Open the mask editor to create a transparent PNG overlay from any image")
        self.create_mask_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0; color: white; border: none;
                border-radius: 3px; font-weight: bold; padding: 6px;
            }
            QPushButton:hover { background-color: #7B1FA2; }
        """)
        self.create_mask_button.clicked.connect(self.open_mask_editor)
        layout.addWidget(self.create_mask_button)
        
        # Requirements
        req_group = QGroupBox("Requirements")
        req_layout = QVBoxLayout()
        
        photo_layout = QHBoxLayout()
        self.require_photo_check = QCheckBox("Require photo capture")
        self.require_photo_check.setToolTip("User must capture photos before proceeding")
        photo_layout.addWidget(self.require_photo_check)
        
        photo_count_label = QLabel("Required count:")
        self.photo_count_spin = QSpinBox()
        self.photo_count_spin.setRange(1, 50)
        self.photo_count_spin.setValue(1)
        self.photo_count_spin.setEnabled(False)
        self.photo_count_spin.setToolTip("Number of photos required for this step")
        self.require_photo_check.toggled.connect(self.photo_count_spin.setEnabled)
        photo_layout.addWidget(photo_count_label)
        photo_layout.addWidget(self.photo_count_spin)
        photo_layout.addStretch()
        req_layout.addLayout(photo_layout)
        
        self.require_annotations_check = QCheckBox("Require annotations")
        self.require_annotations_check.setToolTip("User must add annotation markers to photos")
        req_layout.addWidget(self.require_annotations_check)
        
        self.require_barcode_scan_check = QCheckBox("Require barcode scan")
        self.require_barcode_scan_check.setToolTip("User must scan at least one barcode/QR code before proceeding")
        req_layout.addWidget(self.require_barcode_scan_check)
        
        self.require_pass_fail_check = QCheckBox("Require pass/fail marking")
        self.require_pass_fail_check.setToolTip("User must explicitly mark this step as pass or fail")
        req_layout.addWidget(self.require_pass_fail_check)
        
        req_group.setLayout(req_layout)
        layout.addWidget(req_group)
        
        # Overlay options
        overlay_group = QGroupBox("Overlay Options")
        overlay_layout = QVBoxLayout()
        
        self.transparent_overlay_check = QCheckBox("Use as transparent overlay")
        self.transparent_overlay_check.setToolTip("Overlay image on camera feed respecting transparency (PNG/TIFF/WebP)")
        overlay_layout.addWidget(self.transparent_overlay_check)
        
        self.transparency_note = QLabel("💡 Use PNG format for transparent overlays (alignment guides, measurement grids, etc.)")
        self.transparency_note.setStyleSheet("color: #2196F3; font-size: 9pt; padding: 5px;")
        self.transparency_note.setWordWrap(True)
        overlay_layout.addWidget(self.transparency_note)
        
        self.no_transparency_note = QLabel("(No transparency available - will use blend mode)")
        self.no_transparency_note.setStyleSheet("color: #999; font-style: italic; font-size: 9pt;")
        self.no_transparency_note.setVisible(False)
        overlay_layout.addWidget(self.no_transparency_note)
        
        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def update_checkbox_button(self):
        """Enable/disable checkbox placement button based on image path."""
        path = self.ref_image_input.text().strip()
        self.place_checkboxes_button.setEnabled(bool(path and os.path.exists(path)))
    
    def check_image_transparency(self):
        """Check if selected image has transparency and update UI."""
        import cv2
        path = self.ref_image_input.text().strip()
        
        if not path or not os.path.exists(path):
            return
        
        try:
            # Load image with alpha channel if present
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            
            # Check if image has alpha channel
            has_alpha = len(img.shape) == 3 and img.shape[2] == 4
            
            if has_alpha:
                # Enable transparent overlay option
                self.transparent_overlay_check.setEnabled(True)
                self.transparent_overlay_check.setChecked(True)
                self.transparency_note.setVisible(True)
                self.no_transparency_note.setVisible(False)
            else:
                # Disable transparent overlay option
                self.transparent_overlay_check.setEnabled(False)
                self.transparent_overlay_check.setChecked(False)
                self.transparency_note.setVisible(False)
                self.no_transparency_note.setVisible(True)
        except:
            # If can't load image, disable overlay option
            self.transparent_overlay_check.setEnabled(False)
            self.transparent_overlay_check.setChecked(False)
    
    def place_checkboxes(self):
        """Open dialog to place checkboxes on reference image."""
        image_path = self.ref_image_input.text().strip()
        if not image_path or not os.path.exists(image_path):
            QMessageBox.warning(self, "No Image", "Please select a valid reference image first.")
            return
        
        existing = self.step_data.get('inspection_checkboxes', [])
        dialog = CheckboxPlacementDialog(image_path, existing, self)
        if dialog.exec_() == QDialog.Accepted:
            self.step_data['inspection_checkboxes'] = dialog.get_checkboxes()
            count = len(self.step_data['inspection_checkboxes'])
            QMessageBox.information(self, "Checkboxes Placed", 
                                   f"{count} inspection checkpoint(s) placed.")

    def open_mask_editor(self):
        """Open the mask editor to create a transparent overlay from an image."""
        from gui.mask_editor import MaskEditorDialog
        # Pre-load the current reference image if one is set
        image_path = self.ref_image_input.text().strip()
        if image_path and not os.path.exists(image_path):
            image_path = None
        dialog = MaskEditorDialog(image_path=image_path, parent=self)
        dialog.exec_()
        # If a mask was saved, offer to use it as the reference image
        if dialog.saved_path:
            reply = QMessageBox.question(
                self, "Use Saved Mask",
                f"Use the saved mask as this step's reference image?\n\n{dialog.saved_path}",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.ref_image_input.setText(dialog.saved_path)
                self.check_image_transparency()
    
    def browse_reference_image(self):
        """Browse for reference image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp);;All Files (*)"
        )
        if file_path:
            self.ref_image_input.setText(file_path)
            self.check_image_transparency()
    
    def browse_reference_video(self):
        """Browse for reference video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Video", "",
            "Videos (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;All Files (*)"
        )
        if file_path:
            self.ref_video_input.setText(file_path)
    
    def load_step_data(self):
        """Load existing step data into form."""
        self.title_input.setText(self.step_data.get('title', ''))
        self.instructions_input.setText(self.step_data.get('instructions', ''))
        self.ref_image_input.setText(self.step_data.get('reference_image', ''))
        self.ref_video_input.setText(self.step_data.get('reference_video', ''))
        self.require_photo_check.setChecked(self.step_data.get('require_photo', False))
        self.photo_count_spin.setValue(self.step_data.get('required_photo_count', 1))
        self.photo_count_spin.setEnabled(self.require_photo_check.isChecked())
        self.require_annotations_check.setChecked(self.step_data.get('require_annotations', False))
        self.require_barcode_scan_check.setChecked(self.step_data.get('require_barcode_scan', False))
        self.require_pass_fail_check.setChecked(self.step_data.get('require_pass_fail', False))
        self.transparent_overlay_check.setChecked(self.step_data.get('transparent_overlay', False))
        
        # Check transparency if image is set
        if self.ref_image_input.text().strip():
            self.check_image_transparency()
    
    def get_step_data(self):
        """Get step data from form."""
        data = {
            'title': self.title_input.text().strip(),
            'instructions': self.instructions_input.toPlainText().strip(),
            'reference_image': self.ref_image_input.text().strip(),
            'reference_video': self.ref_video_input.text().strip(),
            'require_photo': self.require_photo_check.isChecked(),
            'required_photo_count': self.photo_count_spin.value() if self.require_photo_check.isChecked() else 1,
            'require_annotations': self.require_annotations_check.isChecked(),
            'require_barcode_scan': self.require_barcode_scan_check.isChecked(),
            'require_pass_fail': self.require_pass_fail_check.isChecked(),
            'transparent_overlay': self.transparent_overlay_check.isChecked()
        }
        
        # Include inspection checkboxes if they were placed
        if 'inspection_checkboxes' in self.step_data:
            data['inspection_checkboxes'] = self.step_data['inspection_checkboxes']
        
        return data


class WorkflowEditorScreen(QWidget):
    """Editor for creating and modifying workflows."""
    
    back_requested = pyqtSignal()
    
    def __init__(self, mode_number, workflow_dir):
        super().__init__()
        self.mode_number = mode_number
        self.workflow_dir = workflow_dir
        self.current_workflow = None
        self.current_workflow_path = None
        self.has_unsaved_changes = False
        self.saved_state = None
        
        self.init_ui()
        self.load_workflows()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        mode_name = "QC Process" if self.mode_number == 2 else "Maintenance/Repair"
        title = QLabel(f"Workflow Editor - {mode_name}")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            background-color: #FFA726;
            color: white;
            padding: 15px;
            border-radius: 5px;
        """)
        layout.addWidget(title)
        
        # Main content - split between workflow list and editor
        content_layout = QHBoxLayout()
        
        # Left side - Workflow list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        list_label = QLabel("Workflows:")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(list_label)
        
        self.workflow_list = QListWidget()
        self.workflow_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #FFA726;
                border-radius: 3px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #FFA726;
                color: white;
            }
        """)
        self.workflow_list.itemClicked.connect(self.on_workflow_selected)
        left_layout.addWidget(self.workflow_list)
        
        # Workflow management buttons
        wf_btn_layout = QVBoxLayout()
        
        self.new_workflow_btn = QPushButton("New Workflow")
        self.new_workflow_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        self.new_workflow_btn.clicked.connect(self.new_workflow)
        wf_btn_layout.addWidget(self.new_workflow_btn)
        
        self.delete_workflow_btn = QPushButton("Delete Workflow")
        self.delete_workflow_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.delete_workflow_btn.clicked.connect(self.delete_workflow)
        self.delete_workflow_btn.setEnabled(False)
        wf_btn_layout.addWidget(self.delete_workflow_btn)
        
        self.export_workflow_btn = QPushButton("Export Workflow")
        self.export_workflow_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 3px;
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
        self.export_workflow_btn.clicked.connect(self.export_workflow)
        self.export_workflow_btn.setEnabled(False)
        wf_btn_layout.addWidget(self.export_workflow_btn)
        
        self.export_instructions_btn = QPushButton("📋 Export as Document")
        self.export_instructions_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px;
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
        self.export_instructions_btn.clicked.connect(self.export_instructions)
        self.export_instructions_btn.setEnabled(False)
        wf_btn_layout.addWidget(self.export_instructions_btn)
        
        self.import_workflow_btn = QPushButton("Import Workflow")
        self.import_workflow_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.import_workflow_btn.clicked.connect(self.import_workflow)
        wf_btn_layout.addWidget(self.import_workflow_btn)
        
        left_layout.addLayout(wf_btn_layout)
        content_layout.addWidget(left_widget)
        
        # Right side - Workflow editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Workflow name
        name_layout = QHBoxLayout()
        name_label = QLabel("Workflow Name:")
        name_label.setStyleSheet("font-weight: bold;")
        self.workflow_name_input = QLineEdit()
        self.workflow_name_input.setPlaceholderText("Enter workflow name...")
        self.workflow_name_input.textChanged.connect(self.mark_unsaved)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.workflow_name_input)
        right_layout.addLayout(name_layout)
        
        # Workflow description
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(desc_label)
        
        self.workflow_desc_input = QTextEdit()
        self.workflow_desc_input.setPlaceholderText("Brief description of this workflow...")
        self.workflow_desc_input.setMaximumHeight(80)
        self.workflow_desc_input.textChanged.connect(self.mark_unsaved)
        right_layout.addWidget(self.workflow_desc_input)
        
        # Steps
        steps_label = QLabel("Steps:")
        steps_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(steps_label)
        
        self.steps_list = QListWidget()
        self.steps_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #77C25E;
                border-radius: 3px;
            }
        """)
        right_layout.addWidget(self.steps_list)
        
        # Step management buttons
        step_btn_layout = QHBoxLayout()
        
        self.add_step_btn = QPushButton("Add Step")
        self.add_step_btn.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                padding: 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
        """)
        self.add_step_btn.clicked.connect(self.add_step)
        step_btn_layout.addWidget(self.add_step_btn)
        
        self.edit_step_btn = QPushButton("Edit Step")
        self.edit_step_btn.clicked.connect(self.edit_step)
        step_btn_layout.addWidget(self.edit_step_btn)
        
        self.delete_step_btn = QPushButton("Delete Step")
        self.delete_step_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                padding: 8px;
                border-radius: 3px;
            }
        """)
        self.delete_step_btn.clicked.connect(self.delete_step)
        step_btn_layout.addWidget(self.delete_step_btn)
        
        self.move_up_btn = QPushButton("↑")
        self.move_up_btn.setMaximumWidth(40)
        self.move_up_btn.clicked.connect(self.move_step_up)
        step_btn_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("↓")
        self.move_down_btn.setMaximumWidth(40)
        self.move_down_btn.clicked.connect(self.move_step_down)
        step_btn_layout.addWidget(self.move_down_btn)
        
        right_layout.addLayout(step_btn_layout)
        
        content_layout.addWidget(right_widget)
        content_layout.setStretch(0, 1)
        content_layout.setStretch(1, 2)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Workflow")
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        self.save_btn.clicked.connect(self.save_workflow)
        bottom_layout.addWidget(self.save_btn)
        
        self.back_btn = QPushButton("Back")
        self.back_btn.setMinimumHeight(50)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.back_btn.clicked.connect(self.on_back_clicked)
        bottom_layout.addWidget(self.back_btn)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
    
    def mark_unsaved(self):
        """Mark that there are unsaved changes."""
        self.has_unsaved_changes = True
    
    def get_current_state(self):
        """Get current editor state as JSON string for comparison."""
        if not self.current_workflow:
            return None
        state = {
            'name': self.workflow_name_input.text().strip(),
            'description': self.workflow_desc_input.toPlainText().strip(),
            'steps': self.current_workflow.get('steps', [])
        }
        return json.dumps(state, sort_keys=True)
    
    def check_unsaved_changes(self):
        """Check if there are unsaved changes and prompt user."""
        if not self.has_unsaved_changes:
            return True
        
        current_state = self.get_current_state()
        if current_state == self.saved_state:
            return True
        
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Do you want to save before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )
        
        if reply == QMessageBox.Save:
            self.save_workflow()
            return True
        elif reply == QMessageBox.Discard:
            return True
        else:  # Cancel
            return False
    
    def on_back_clicked(self):
        """Handle back button with unsaved changes check."""
        if self.check_unsaved_changes():
            self.back_requested.emit()
    
    def load_workflows(self):
        """Load workflows from directory."""
        self.workflow_list.clear()
        
        if not os.path.exists(self.workflow_dir):
            os.makedirs(self.workflow_dir, exist_ok=True)
            return
        
        for filename in os.listdir(self.workflow_dir):
            if filename.endswith('.json'):
                self.workflow_list.addItem(filename[:-5])  # Remove .json extension
    
    def on_workflow_selected(self, item):
        """Load selected workflow for editing."""
        # Check for unsaved changes before switching
        if not self.check_unsaved_changes():
            return
        
        workflow_name = item.text()
        filepath = os.path.join(self.workflow_dir, f"{workflow_name}.json")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.current_workflow = json.load(f)
                self.current_workflow_path = filepath
            
            self.load_workflow_to_editor()
            self.delete_workflow_btn.setEnabled(True)
            self.export_workflow_btn.setEnabled(True)
            self.export_instructions_btn.setEnabled(True)
            self.has_unsaved_changes = False
            self.saved_state = self.get_current_state()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load workflow: {e}")
    
    def load_workflow_to_editor(self):
        """Load current workflow into editor fields."""
        if not self.current_workflow:
            return
        
        self.workflow_name_input.setText(self.current_workflow.get('name', ''))
        self.workflow_desc_input.setText(self.current_workflow.get('description', ''))
        
        self.steps_list.clear()
        for i, step in enumerate(self.current_workflow.get('steps', [])):
            title = step.get('title', f'Step {i+1}')
            self.steps_list.addItem(f"{i+1}. {title}")
    
    def new_workflow(self):
        """Create a new workflow."""
        # Check for unsaved changes before creating new
        if not self.check_unsaved_changes():
            return
        
        self.current_workflow = {
            'name': '',
            'description': '',
            'steps': []
        }
        self.current_workflow_path = None
        
        self.workflow_name_input.clear()
        self.workflow_desc_input.clear()
        self.steps_list.clear()
        self.delete_workflow_btn.setEnabled(False)
        self.has_unsaved_changes = False
        self.saved_state = self.get_current_state()
    
    def delete_workflow(self):
        """Delete the current workflow."""
        if not self.current_workflow_path:
            return
        
        reply = QMessageBox.question(self, "Delete Workflow",
                                     "Are you sure you want to delete this workflow?",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(self.current_workflow_path)
                self.load_workflows()
                self.new_workflow()
                QMessageBox.information(self, "Success", "Workflow deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete workflow: {e}")
    
    def add_step(self):
        """Add a new step."""
        dialog = StepEditorDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            step_data = dialog.get_step_data()
            if not step_data['title']:
                QMessageBox.warning(self, "Invalid Step", "Step title is required.")
                return
            
            if not self.current_workflow:
                self.current_workflow = {'name': '', 'description': '', 'steps': []}
            
            self.current_workflow['steps'].append(step_data)
            self.load_workflow_to_editor()
            self.mark_unsaved()
    
    def edit_step(self):
        """Edit selected step."""
        current_row = self.steps_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a step to edit.")
            return
        
        step_data = self.current_workflow['steps'][current_row]
        dialog = StepEditorDialog(step_data, parent=self)
        
        if dialog.exec_() == QDialog.Accepted:
            self.current_workflow['steps'][current_row] = dialog.get_step_data()
            self.load_workflow_to_editor()
            self.mark_unsaved()
    
    def delete_step(self):
        """Delete selected step."""
        current_row = self.steps_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a step to delete.")
            return
        
        reply = QMessageBox.question(self, "Delete Step",
                                     "Are you sure you want to delete this step?",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.current_workflow['steps'].pop(current_row)
            self.load_workflow_to_editor()
            self.mark_unsaved()
    
    def move_step_up(self):
        """Move selected step up."""
        current_row = self.steps_list.currentRow()
        if current_row <= 0:
            return
        
        steps = self.current_workflow['steps']
        steps[current_row], steps[current_row - 1] = steps[current_row - 1], steps[current_row]
        self.load_workflow_to_editor()
        self.steps_list.setCurrentRow(current_row - 1)
        self.mark_unsaved()
    
    def move_step_down(self):
        """Move selected step down."""
        current_row = self.steps_list.currentRow()
        if current_row < 0 or current_row >= len(self.current_workflow['steps']) - 1:
            return
        
        steps = self.current_workflow['steps']
        steps[current_row], steps[current_row + 1] = steps[current_row + 1], steps[current_row]
        self.load_workflow_to_editor()
        self.steps_list.setCurrentRow(current_row + 1)
        self.mark_unsaved()
    
    def save_workflow(self):
        """Save the current workflow."""
        if not self.current_workflow:
            QMessageBox.warning(self, "No Workflow", "Create a new workflow first.")
            return
        
        # Update workflow from editor
        name = self.workflow_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Workflow name is required.")
            return
        
        self.current_workflow['name'] = name
        self.current_workflow['description'] = self.workflow_desc_input.toPlainText().strip()
        
        if not self.current_workflow['steps']:
            QMessageBox.warning(self, "No Steps", "Add at least one step to the workflow.")
            return
        
        # Determine save path
        new_filename = f"{name.replace(' ', '_').lower()}.json"
        new_filepath = os.path.join(self.workflow_dir, new_filename)
        
        # Check if we're editing an existing workflow
        if self.current_workflow_path and os.path.exists(self.current_workflow_path):
            # Editing existing workflow
            old_filename = os.path.basename(self.current_workflow_path)
            
            if new_filename != old_filename:
                # Name changed - ask user what to do
                reply = QMessageBox.question(
                    self,
                    "Workflow Name Changed",
                    f"The workflow name has changed.\n\n"
                    f"Old: {old_filename}\n"
                    f"New: {new_filename}\n\n"
                    f"Do you want to:\n"
                    f"• Yes: Rename the workflow (delete old file)\n"
                    f"• No: Save as new workflow (keep both)",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Cancel:
                    return
                elif reply == QMessageBox.Yes:
                    # Rename - delete old file
                    try:
                        os.remove(self.current_workflow_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Warning", f"Could not delete old file: {e}")
                # If No, just save as new file (keep both)
            else:
                # Same name - just update the file
                new_filepath = self.current_workflow_path
        
        # Save to file
        try:
            with open(new_filepath, 'w') as f:
                json.dump(self.current_workflow, f, indent=2)
            
            self.current_workflow_path = new_filepath
            self.has_unsaved_changes = False
            self.saved_state = self.get_current_state()
            QMessageBox.information(self, "Success", f"Workflow saved: {new_filename}")
            self.load_workflows()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save workflow: {e}")
    
    def export_instructions(self):
        """Generate a printable instruction PDF for the current workflow."""
        if not self.current_workflow:
            QMessageBox.warning(self, "No Workflow", "Select a workflow to export instructions.")
            return
        
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "output", "reports")
        pdf_path = _generate_instructions(self.current_workflow, output_dir)
        if pdf_path and os.path.exists(pdf_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(pdf_path)
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", pdf_path])
                else:
                    subprocess.Popen(["xdg-open", pdf_path])
            except Exception:
                pass
            QMessageBox.information(self, "Instructions Generated",
                f"Saved to:\n{pdf_path}")
        else:
            QMessageBox.warning(self, "Error", "Failed to generate instruction document.")

    def export_workflow(self):
        """Export workflow as a zip file with all reference images."""
        if not self.current_workflow or not self.current_workflow_path:
            QMessageBox.warning(self, "No Workflow", "Select a workflow to export.")
            return
        
        # Get workflow name for default filename
        workflow_name = self.current_workflow.get('name', 'workflow')
        safe_name = workflow_name.replace(' ', '_').lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"{safe_name}_{timestamp}.zip"
        
        # Ask user where to save
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Workflow",
            default_filename,
            "Workflow Package (*.zip)"
        )
        
        if not save_path:
            return
        
        try:
            # Determine resource directory based on mode
            if self.mode_number == 2:
                resource_dir = "resources/qc_reference_images"
            else:
                resource_dir = "resources/maintenance_reference_images"
            
            # Create absolute path to resource directory
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            resource_abs_path = os.path.join(app_root, resource_dir)
            os.makedirs(resource_abs_path, exist_ok=True)
            
            # Collect all reference images
            image_files = []
            for step in self.current_workflow.get('steps', []):
                ref_image = step.get('reference_image', '')
                if ref_image and os.path.exists(ref_image):
                    image_files.append(ref_image)
            
            # Create zip file
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add workflow JSON
                zipf.write(self.current_workflow_path, 'workflow.json')
                
                # Add reference images
                for img_path in image_files:
                    # Use just the filename for the archive
                    img_filename = os.path.basename(img_path)
                    zipf.write(img_path, f"images/{img_filename}")
                
                # Create manifest
                manifest = {
                    'workflow_name': workflow_name,
                    'mode': self.mode_number,
                    'export_date': datetime.now().isoformat(),
                    'image_count': len(image_files),
                    'version': '1.0'
                }
                zipf.writestr('manifest.json', json.dumps(manifest, indent=2))
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Workflow exported successfully!\n\n"
                f"File: {os.path.basename(save_path)}\n"
                f"Images included: {len(image_files)}"
            )
        
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export workflow:\n{e}")
    
    def import_workflow(self):
        """Import workflow from a zip package or JSON file."""
        # Ask user to select file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Workflow",
            "",
            "Workflow Files (*.zip *.json);;Workflow Package (*.zip);;Workflow JSON (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.lower().endswith('.json'):
                self._import_workflow_json(file_path)
            else:
                self._import_workflow_zip(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to import workflow:\n{e}")

    def _import_workflow_json(self, file_path):
        """Import a raw workflow JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        if not isinstance(workflow, dict) or 'steps' not in workflow:
            raise ValueError("Invalid workflow file: must contain a 'steps' array")

        workflow_name = workflow.get('name', os.path.splitext(os.path.basename(file_path))[0])
        workflow.setdefault('name', workflow_name)
        safe_name = workflow_name.replace(' ', '_').lower()
        target_path = os.path.join(self.workflow_dir, f"{safe_name}.json")

        if os.path.exists(target_path):
            reply = QMessageBox.question(
                self, "Workflow Exists",
                f"A workflow named '{workflow_name}' already exists.\n\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_name = f"{safe_name}_{timestamp}"
                workflow['name'] = f"{workflow_name} ({timestamp})"
                target_path = os.path.join(self.workflow_dir, f"{safe_name}.json")

        # Check for reference images with invalid paths
        missing_images = []
        for step in workflow.get('steps', []):
            ref = step.get('reference_image', '')
            if ref and not os.path.exists(ref):
                missing_images.append(f"Step '{step.get('title', '?')}': {ref}")

        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, indent=2)

        self.load_workflows()

        msg = f"Workflow imported successfully!\n\nName: {workflow['name']}\nSteps: {len(workflow.get('steps', []))}"
        if missing_images:
            msg += f"\n\n⚠️ {len(missing_images)} reference image(s) not found:\n"
            msg += "\n".join(missing_images[:5])
            if len(missing_images) > 5:
                msg += f"\n...and {len(missing_images) - 5} more"
            msg += "\n\nYou can update image paths in the workflow editor."
        QMessageBox.information(self, "Import Successful", msg)

    def _import_workflow_zip(self, file_path):
        """Import workflow from a zip package with bundled images."""
        # Determine resource directory based on mode
        if self.mode_number == 2:
            resource_dir = "resources/qc_reference_images"
        else:
            resource_dir = "resources/maintenance_reference_images"
        
        # Create absolute paths
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resource_abs_path = os.path.join(app_root, resource_dir)
        os.makedirs(resource_abs_path, exist_ok=True)
        
        # Extract and validate zip
        with zipfile.ZipFile(file_path, 'r') as zipf:
            # Check for required files
            if 'workflow.json' not in zipf.namelist():
                raise ValueError("Invalid workflow package: missing workflow.json")
            
            # Read manifest if available
            manifest = None
            if 'manifest.json' in zipf.namelist():
                manifest_data = zipf.read('manifest.json')
                manifest = json.loads(manifest_data)
                
                # Check mode compatibility
                if manifest.get('mode') != self.mode_number:
                    mode_name = "QC" if self.mode_number == 2 else "Maintenance"
                    reply = QMessageBox.question(
                        self,
                        "Mode Mismatch",
                        f"This workflow was exported from a different mode.\n\n"
                        f"Current mode: {mode_name}\n"
                        f"Workflow mode: {'QC' if manifest.get('mode') == 2 else 'Maintenance'}\n\n"
                        f"Import anyway?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        return
            
            # Read workflow JSON
            workflow_data = zipf.read('workflow.json')
            workflow = json.loads(workflow_data)
            
            # Check for name conflict
            workflow_name = workflow.get('name', 'imported_workflow')
            safe_name = workflow_name.replace(' ', '_').lower()
            target_path = os.path.join(self.workflow_dir, f"{safe_name}.json")
            
            if os.path.exists(target_path):
                reply = QMessageBox.question(
                    self,
                    "Workflow Exists",
                    f"A workflow named '{workflow_name}' already exists.\n\n"
                    f"Overwrite it?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    # Append timestamp to make unique
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_name = f"{safe_name}_{timestamp}"
                    workflow['name'] = f"{workflow_name} ({timestamp})"
                    target_path = os.path.join(self.workflow_dir, f"{safe_name}.json")
            
            # Extract images and update paths
            image_mapping = {}
            for item in zipf.namelist():
                if item.startswith('images/'):
                    img_filename = os.path.basename(item)
                    target_img_path = os.path.join(resource_abs_path, img_filename)
                    
                    # Extract image
                    with zipf.open(item) as source, open(target_img_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    
                    # Store mapping for path updates
                    image_mapping[img_filename] = os.path.join(resource_dir, img_filename)
            
            # Update reference image paths in workflow
            for step in workflow.get('steps', []):
                ref_image = step.get('reference_image', '')
                if ref_image:
                    img_filename = os.path.basename(ref_image)
                    if img_filename in image_mapping:
                        step['reference_image'] = image_mapping[img_filename]
            
            # Save workflow
            with open(target_path, 'w') as f:
                json.dump(workflow, f, indent=2)
            
            # Reload workflows list
            self.load_workflows()
            
            QMessageBox.information(
                self,
                "Import Successful",
                f"Workflow imported successfully!\n\n"
                f"Name: {workflow['name']}\n"
                f"Images imported: {len(image_mapping)}\n"
                f"Steps: {len(workflow.get('steps', []))}"
            )
