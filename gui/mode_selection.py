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
        self.description_input.setMinimumHeight(80)
        self.description_input.setMaximumHeight(120)
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
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Select a workflow to resume:")
        label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(label)
        
        # Container for list with delete buttons
        from PyQt5.QtWidgets import QScrollArea, QFrame
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setSpacing(5)
        
        selected_progress = {'data': None}
        
        def create_progress_item(pf):
            """Create a progress item widget."""
            item_widget = QWidget()
            item_widget.setStyleSheet("""
                QWidget {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    padding: 10px;
                }
                QWidget:hover {
                    background-color: #e8e8e8;
                }
            """)
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(10, 5, 10, 5)
            
            # Info label
            info_label = QLabel(
                f"<b>{pf['serial']}</b> - {pf['workflow_name']}<br>"
                f"<small>Technician: {pf['technician']} | Step {pf['step']} | {pf['modified']}</small>"
            )
            info_label.setTextFormat(Qt.RichText)
            item_layout.addWidget(info_label)
            
            # Make item clickable
            def select_item(event):
                selected_progress['data'] = pf
                # Highlight selected
                for i in range(list_layout.count()):
                    w = list_layout.itemAt(i).widget()
                    if w and w != item_widget:
                        w.setStyleSheet("""
                            QWidget {
                                background-color: #f5f5f5;
                                border: 1px solid #ddd;
                                border-radius: 3px;
                                padding: 10px;
                            }
                            QWidget:hover {
                                background-color: #e8e8e8;
                            }
                        """)
                item_widget.setStyleSheet("""
                    QWidget {
                        background-color: #e8f5e9;
                        border: 2px solid #77C25E;
                        border-radius: 3px;
                        padding: 10px;
                    }
                """)
            
            item_widget.mousePressEvent = select_item
            
            return item_widget
        
        for pf in progress_files:
            list_layout.addWidget(create_progress_item(pf))
        
        list_layout.addStretch()
        scroll.setWidget(list_container)
        layout.addWidget(scroll)
        
        # Buttons - Resume (left), Cancel (middle), Delete (right)
        button_layout = QHBoxLayout()
        
        resume_btn = QPushButton("Resume Selected")
        resume_btn.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
        """)
        resume_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(resume_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
        """)
        
        def delete_selected():
            if not selected_progress['data']:
                QMessageBox.warning(dialog, "No Selection", "Please select a workflow to delete.")
                return
            
            pf = selected_progress['data']
            reply = QMessageBox.question(dialog, "Delete Progress?",
                                       f"Delete progress for {pf['serial']} - {pf['workflow_name']}?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    os.remove(pf['progress_file'])
                    progress_files.remove(pf)
                    selected_progress['data'] = None
                    
                    # Rebuild list
                    for i in reversed(range(list_layout.count())):
                        widget = list_layout.itemAt(i).widget()
                        if widget:
                            widget.setParent(None)
                            widget.deleteLater()
                    
                    if progress_files:
                        for pf in progress_files:
                            list_layout.addWidget(create_progress_item(pf))
                        list_layout.addStretch()
                    else:
                        QMessageBox.information(dialog, "All Cleared", "No more incomplete workflows.")
                        dialog.reject()
                        
                except Exception as e:
                    QMessageBox.warning(dialog, "Delete Error", f"Failed to delete:\n{str(e)}")
        
        delete_btn.clicked.connect(delete_selected)
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
        
        if dialog.exec_() == QDialog.Accepted and selected_progress['data']:
            pf = selected_progress['data']
            self.resume_workflow.emit(pf['workflow_path'], pf['serial'], pf['technician'])
