"""Mode selection screen - initial application screen."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QButtonGroup, QRadioButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor


class ModeSelectionScreen(QWidget):
    """Initial screen for selecting mode and entering job information."""
    
    mode_selected = pyqtSignal(int, str, str)  # mode, serial_number, description
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set background color
        self.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title with green background
        title = QLabel("Emtech EoAT Cam Viewer")
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
        serial_label.setStyleSheet("color: black; font-weight: bold;")
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("Enter unit serial number (optional)")
        self.serial_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #77C25E;
                border-radius: 3px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #5FA84A;
            }
        """)
        serial_layout.addWidget(serial_label)
        serial_layout.addWidget(self.serial_input)
        layout.addLayout(serial_layout)
        
        # Description input
        desc_layout = QVBoxLayout()
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("color: black; font-weight: bold;")
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter purpose of work")
        self.description_input.setMaximumHeight(80)
        self.description_input.setStyleSheet("""
            QTextEdit {
                padding: 8px;
                border: 2px solid #77C25E;
                border-radius: 3px;
                background-color: white;
            }
            QTextEdit:focus {
                border: 2px solid #5FA84A;
            }
        """)
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.description_input)
        layout.addLayout(desc_layout)
        
        layout.addSpacing(10)
        
        # Mode selection
        mode_label = QLabel("Select Mode:")
        mode_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        mode_label.setStyleSheet("color: black;")
        layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup()
        
        # Mode 1
        mode1_radio = QRadioButton("Mode 1: General Image Capture")
        mode1_radio.setFont(QFont("Arial", 12))
        mode1_radio.setStyleSheet("color: black;")
        self.mode_group.addButton(mode1_radio, 1)
        layout.addWidget(mode1_radio)
        
        mode1_desc = QLabel("    Capture images and videos from any camera source")
        mode1_desc.setStyleSheet("color: #666666;")
        layout.addWidget(mode1_desc)
        
        # Mode 2
        mode2_radio = QRadioButton("Mode 2: QC Process")
        mode2_radio.setFont(QFont("Arial", 12))
        mode2_radio.setStyleSheet("color: black;")
        self.mode_group.addButton(mode2_radio, 2)
        layout.addWidget(mode2_radio)
        
        mode2_desc = QLabel("    Guided quality control workflow with checklist and report generation")
        mode2_desc.setStyleSheet("color: #666666;")
        layout.addWidget(mode2_desc)
        
        # Mode 3
        mode3_radio = QRadioButton("Mode 3: Maintenance/Repair")
        mode3_radio.setFont(QFont("Arial", 12))
        mode3_radio.setStyleSheet("color: black;")
        self.mode_group.addButton(mode3_radio, 3)
        layout.addWidget(mode3_radio)
        
        mode3_desc = QLabel("    Guided maintenance and repair procedures with documentation")
        mode3_desc.setStyleSheet("color: #666666;")
        layout.addWidget(mode3_desc)
        
        layout.addStretch()
        
        # Start button with green styling
        self.start_button = QPushButton("Start")
        self.start_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.start_button.setMinimumHeight(50)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
            QPushButton:pressed {
                background-color: #4D8A3C;
            }
        """)
        self.start_button.clicked.connect(self.on_start_clicked)
        layout.addWidget(self.start_button)
        
        self.setLayout(layout)
    
    def on_start_clicked(self):
        """Handle start button click."""
        serial = self.serial_input.text().strip()
        description = self.description_input.toPlainText().strip()
        selected_mode = self.mode_group.checkedId()
        
        # Serial number is now optional
        self.serial_input.setStyleSheet("")
        
        if selected_mode == -1:
            return
        
        self.mode_selected.emit(selected_mode, serial, description)
