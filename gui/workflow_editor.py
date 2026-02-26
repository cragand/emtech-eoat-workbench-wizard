"""Workflow editor for creating and modifying QC and maintenance workflows."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QMessageBox, QLineEdit, 
                             QTextEdit, QCheckBox, QFileDialog, QDialog, QDialogButtonBox,
                             QScrollArea, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QPen
import os
import json


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
        
        # Checkbox placement button
        self.place_checkboxes_button = QPushButton("📍 Place Inspection Checkboxes")
        self.place_checkboxes_button.setToolTip("Add checkboxes on reference image for inspection points")
        self.place_checkboxes_button.clicked.connect(self.place_checkboxes)
        self.place_checkboxes_button.setEnabled(False)
        self.ref_image_input.textChanged.connect(self.update_checkbox_button)
        layout.addWidget(self.place_checkboxes_button)
        
        # Requirements
        req_group = QGroupBox("Requirements")
        req_layout = QVBoxLayout()
        
        self.require_photo_check = QCheckBox("Require photo capture")
        self.require_photo_check.setToolTip("User must capture at least one photo before proceeding")
        req_layout.addWidget(self.require_photo_check)
        
        self.require_annotations_check = QCheckBox("Require annotations")
        self.require_annotations_check.setToolTip("User must add annotation markers to photos")
        req_layout.addWidget(self.require_annotations_check)
        
        self.require_pass_fail_check = QCheckBox("Require pass/fail marking")
        self.require_pass_fail_check.setToolTip("User must explicitly mark this step as pass or fail")
        req_layout.addWidget(self.require_pass_fail_check)
        
        req_group.setLayout(req_layout)
        layout.addWidget(req_group)
        
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
    
    def browse_reference_image(self):
        """Browse for reference image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if file_path:
            self.ref_image_input.setText(file_path)
    
    def load_step_data(self):
        """Load existing step data into form."""
        self.title_input.setText(self.step_data.get('title', ''))
        self.instructions_input.setText(self.step_data.get('instructions', ''))
        self.ref_image_input.setText(self.step_data.get('reference_image', ''))
        self.require_photo_check.setChecked(self.step_data.get('require_photo', False))
        self.require_annotations_check.setChecked(self.step_data.get('require_annotations', False))
        self.require_pass_fail_check.setChecked(self.step_data.get('require_pass_fail', False))
    
    def get_step_data(self):
        """Get step data from form."""
        data = {
            'title': self.title_input.text().strip(),
            'instructions': self.instructions_input.toPlainText().strip(),
            'reference_image': self.ref_image_input.text().strip(),
            'require_photo': self.require_photo_check.isChecked(),
            'require_annotations': self.require_annotations_check.isChecked(),
            'require_pass_fail': self.require_pass_fail_check.isChecked()
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
            with open(filepath, 'r') as f:
                self.current_workflow = json.load(f)
                self.current_workflow_path = filepath
            
            self.load_workflow_to_editor()
            self.delete_workflow_btn.setEnabled(True)
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
