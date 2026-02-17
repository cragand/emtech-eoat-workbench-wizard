"""Workflow selection screen for Mode 2 and Mode 3."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QMessageBox, QLineEdit, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import os
import json


class PasswordDialog(QDialog):
    """Simple password dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        label = QLabel("Enter password to access workflow editor:")
        layout.addWidget(label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    def get_password(self):
        return self.password_input.text()


class WorkflowSelectionScreen(QWidget):
    """Screen for selecting or editing workflows."""
    
    workflow_selected = pyqtSignal(str)  # Emits workflow file path
    edit_workflows = pyqtSignal()  # Emits when user wants to edit
    back_requested = pyqtSignal()  # Emits when user wants to go back
    
    def __init__(self, mode_number, workflow_dir):
        super().__init__()
        self.mode_number = mode_number
        self.workflow_dir = workflow_dir
        self.password = "admin"  # Simple password (can be changed)
        
        self.init_ui()
        self.load_workflows()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        mode_name = "QC Process" if self.mode_number == 2 else "Maintenance/Repair"
        title = QLabel(f"Mode {self.mode_number}: {mode_name}")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            background-color: #77C25E;
            color: white;
            padding: 20px;
            border-radius: 5px;
        """)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("Select a workflow to begin:")
        instructions.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(instructions)
        
        # Workflow list
        self.workflow_list = QListWidget()
        self.workflow_list.itemDoubleClicked.connect(self.on_workflow_double_clicked)
        self.workflow_list.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.workflow_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Workflow")
        self.start_button.setMinimumHeight(50)
        self.start_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.start_button.clicked.connect(self.on_start_clicked)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        self.edit_button = QPushButton("Edit Workflows")
        self.edit_button.setMinimumHeight(50)
        self.edit_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #FFA726;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #FB8C00;
            }
        """)
        self.edit_button.clicked.connect(self.on_edit_clicked)
        button_layout.addWidget(self.edit_button)
        
        self.back_button = QPushButton("Back to Menu")
        self.back_button.setMinimumHeight(50)
        self.back_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.back_button.clicked.connect(self.back_requested.emit)
        button_layout.addWidget(self.back_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_workflows(self):
        """Load available workflows from directory."""
        self.workflow_list.clear()
        self.workflows = []
        
        if not os.path.exists(self.workflow_dir):
            os.makedirs(self.workflow_dir, exist_ok=True)
            return
        
        # Load all JSON files
        for filename in os.listdir(self.workflow_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.workflow_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        workflow = json.load(f)
                        workflow['filepath'] = filepath
                        self.workflows.append(workflow)
                        
                        # Add to list
                        display_name = workflow.get('name', filename)
                        description = workflow.get('description', '')
                        item_text = f"{display_name}\n  {description}" if description else display_name
                        self.workflow_list.addItem(item_text)
                except Exception as e:
                    print(f"Error loading workflow {filename}: {e}")
        
        if not self.workflows:
            self.workflow_list.addItem("No workflows found. Click 'Edit Workflows' to create one.")
    
    def on_workflow_double_clicked(self, item):
        """Handle double-click on workflow."""
        self.on_start_clicked()
    
    def on_start_clicked(self):
        """Handle start button click."""
        selected_row = self.workflow_list.currentRow()
        if selected_row >= 0 and selected_row < len(self.workflows):
            workflow = self.workflows[selected_row]
            self.workflow_selected.emit(workflow['filepath'])
    
    def on_edit_clicked(self):
        """Handle edit button click - require password."""
        dialog = PasswordDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.get_password() == self.password:
                self.edit_workflows.emit()
            else:
                QMessageBox.warning(self, "Access Denied", "Incorrect password.")
    
    def on_selection_changed(self):
        """Enable start button when workflow is selected."""
        self.start_button.setEnabled(self.workflow_list.currentRow() >= 0 and len(self.workflows) > 0)

