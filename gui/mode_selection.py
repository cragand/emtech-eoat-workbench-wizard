"""Mode selection screen - initial application screen."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QButtonGroup, QRadioButton, QMessageBox, QDialog, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import os
import json
from datetime import datetime


class ModeSelectionScreen(QWidget):
    """Initial screen for selecting mode and entering job information."""
    
    mode_selected = pyqtSignal(int, str, str, str)  # mode, serial_number, technician, description
    resume_workflow = pyqtSignal(str, str, str)  # workflow_path, serial_number, technician
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title with green background
        title = QLabel("Emtech EoAT Workbench Wizard")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            background-color: #77C25E;
            color: white;
            padding: 20px;
            border-radius: 5px;
        """)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # Serial number input
        serial_layout = QHBoxLayout()
        serial_label = QLabel("Serial Number:")
        serial_label.setMinimumWidth(150)
        serial_label.setStyleSheet("font-weight: bold;")
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("Serial number (or title)")
        serial_layout.addWidget(serial_label)
        serial_layout.addWidget(self.serial_input)
        layout.addLayout(serial_layout)
        
        # Technician name input
        tech_layout = QHBoxLayout()
        tech_label = QLabel("Technician Name:")
        tech_label.setMinimumWidth(150)
        tech_label.setStyleSheet("font-weight: bold;")
        self.tech_input = QLineEdit()
        self.tech_input.setPlaceholderText("Your name")
        tech_layout.addWidget(tech_label)
        tech_layout.addWidget(self.tech_input)
        layout.addLayout(tech_layout)
        
        # Description input
        desc_layout = QVBoxLayout()
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold;")
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter purpose of work")
        self.description_input.setMaximumHeight(80)
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.description_input)
        layout.addLayout(desc_layout)
        
        layout.addSpacing(10)
        
        # Mode selection
        mode_label = QLabel("Select Mode:")
        mode_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup()
        
        # Mode 1
        mode1_radio = QRadioButton("Mode 1: General Image Capture")
        mode1_radio.setFont(QFont("Arial", 12))
        self.mode_group.addButton(mode1_radio, 1)
        layout.addWidget(mode1_radio)
        
        mode1_desc = QLabel("    Capture images and videos from any camera source")
        mode1_desc.setStyleSheet("color: #888888;")
        layout.addWidget(mode1_desc)
        
        # Mode 2
        mode2_radio = QRadioButton("Mode 2: QC Process")
        mode2_radio.setFont(QFont("Arial", 12))
        self.mode_group.addButton(mode2_radio, 2)
        layout.addWidget(mode2_radio)
        
        mode2_desc = QLabel("    Guided quality control workflow with checklist and report generation")
        mode2_desc.setStyleSheet("color: #888888;")
        layout.addWidget(mode2_desc)
        
        # Mode 3
        mode3_radio = QRadioButton("Mode 3: Maintenance/Repair")
        mode3_radio.setFont(QFont("Arial", 12))
        self.mode_group.addButton(mode3_radio, 3)
        layout.addWidget(mode3_radio)
        
        mode3_desc = QLabel("    Guided maintenance and repair procedures with documentation")
        mode3_desc.setStyleSheet("color: #888888;")
        layout.addWidget(mode3_desc)
        
        layout.addStretch()
        
        # Start button - let theme handle styling
        self.start_button = QPushButton("Start")
        self.start_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(self.on_start_clicked)
        layout.addWidget(self.start_button)
        
        # Resume button - small and unobtrusive
        self.resume_button = QPushButton("📂 Resume Incomplete Workflow")
        self.resume_button.setMaximumHeight(30)
        self.resume_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: 1px solid #888888;
                border-radius: 3px;
                padding: 5px 10px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                color: #555555;
                border-color: #555555;
            }
        """)
        self.resume_button.clicked.connect(self.on_resume_clicked)
        layout.addWidget(self.resume_button)
        
        self.setLayout(layout)
    
    def on_start_clicked(self):
        """Handle start button click."""
        serial = self.serial_input.text().strip()
        technician = self.tech_input.text().strip()
        description = self.description_input.toPlainText().strip()
        selected_mode = self.mode_group.checkedId()
        
        # Serial number is required
        if not serial:
            QMessageBox.warning(self, "Serial Number Required", 
                               "Please enter a serial number before starting.")
            self.serial_input.setStyleSheet("border: 2px solid red;")
            return
        
        self.serial_input.setStyleSheet("")
        
        # Technician name is required
        if not technician:
            QMessageBox.warning(self, "Technician Name Required", 
                               "Please enter your name before starting.")
            self.tech_input.setStyleSheet("border: 2px solid red;")
            return
        
        self.tech_input.setStyleSheet("")
        
        if selected_mode == -1:
            return
        
        self.mode_selected.emit(selected_mode, serial, technician, description)
    
    def on_resume_clicked(self):
        """Show dialog to select incomplete workflow to resume."""
        # Find all progress files
        output_base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   "output", "captured_images")
        
        progress_files = []
        if os.path.exists(output_base):
            for serial_dir in os.listdir(output_base):
                serial_path = os.path.join(output_base, serial_dir)
                if os.path.isdir(serial_path):
                    progress_file = os.path.join(serial_path, "_workflow_progress.json")
                    if os.path.exists(progress_file):
                        try:
                            # Check age (skip if older than 30 days)
                            file_age_days = (datetime.now().timestamp() - os.path.getmtime(progress_file)) / 86400
                            if file_age_days > 30:
                                continue
                            
                            with open(progress_file, 'r') as f:
                                data = json.load(f)
                            
                            workflow_path = data.get('workflow_path', '')
                            workflow_name = os.path.basename(workflow_path).replace('.json', '').replace('_', ' ').title()
                            
                            progress_files.append({
                                'serial': data.get('serial_number', serial_dir),
                                'technician': data.get('technician', 'Unknown'),
                                'workflow_name': workflow_name,
                                'workflow_path': workflow_path,
                                'step': data.get('current_step', 0) + 1,
                                'total_steps': len(data.get('step_results', {})),
                                'modified': datetime.fromtimestamp(os.path.getmtime(progress_file)).strftime("%Y-%m-%d %H:%M"),
                                'progress_file': progress_file
                            })
                        except:
                            pass
        
        if not progress_files:
            QMessageBox.information(self, "No Incomplete Workflows", 
                                   "No incomplete workflows found.")
            return
        
        # Show selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Resume Incomplete Workflow")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Select a workflow to resume:")
        label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        list_widget.setStyleSheet("font-size: 11px;")
        
        for pf in progress_files:
            item_text = (f"{pf['serial']} - {pf['workflow_name']}\n"
                        f"  Technician: {pf['technician']} | Step {pf['step']} | Last modified: {pf['modified']}")
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, pf)
            list_widget.addItem(item)
        
        list_widget.itemDoubleClicked.connect(lambda: dialog.accept())
        layout.addWidget(list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        resume_btn = QPushButton("Resume Selected")
        resume_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(resume_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            selected_item = list_widget.currentItem()
            if selected_item:
                pf = selected_item.data(Qt.UserRole)
                self.resume_workflow.emit(pf['workflow_path'], pf['serial'], pf['technician'])
