"""Mode selection screen - initial application screen."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QButtonGroup, QRadioButton, QMessageBox, QDialog, QListWidget, QListWidgetItem, QComboBox, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QImage, QPixmap
import os
import json
import cv2
from datetime import datetime
from camera import CameraManager
from gui.camera_settings_dialog import CameraSettingsDialog
from theme_manager import theme_manager
from workflows.workflow_loader import WorkflowLoader
from reports.workflow_instructions_generator import generate_workflow_instructions

# Optional barcode scanner support
try:
    from qr_scanner import QRScannerThread
    QR_SCANNER_AVAILABLE = True
except ImportError:
    QR_SCANNER_AVAILABLE = False
    QRScannerThread = None


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
        
        # Serial number input with scan button
        serial_layout = QHBoxLayout()
        serial_label = QLabel("Serial Number:")
        serial_label.setMinimumWidth(150)
        serial_label.setStyleSheet("font-weight: bold;")
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("Serial number (or title)")
        self.serial_input.setMaximumWidth(400)
        
        scan_serial_button = QPushButton("Scan Serial QR/Barcode")
        scan_serial_button.setMaximumWidth(270)
        scan_serial_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
        """)
        scan_serial_button.clicked.connect(self.open_serial_scan_dialog)
        
        serial_layout.addWidget(serial_label)
        serial_layout.addWidget(self.serial_input)
        serial_layout.addWidget(scan_serial_button)
        serial_layout.addStretch()
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
        
        # Bottom buttons row
        bottom_buttons_layout = QHBoxLayout()
        
        # Camera Settings button
        self.camera_settings_button = QPushButton("⚙️ Camera Settings")
        self.camera_settings_button.setMaximumHeight(30)
        self.camera_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.camera_settings_button.clicked.connect(self.open_camera_settings)
        bottom_buttons_layout.addWidget(self.camera_settings_button)
        
        bottom_buttons_layout.addStretch()
        
        # View Reports button
        self.view_reports_button = QPushButton("📁 View Reports")
        self.view_reports_button.setMaximumHeight(30)
        self.view_reports_button.setStyleSheet("""
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
        self.view_reports_button.clicked.connect(self.on_view_reports_clicked)
        bottom_buttons_layout.addWidget(self.view_reports_button)
        
        # Workflow Instruction Documents button
        self.instructions_button = QPushButton("📋 Workflow Instruction Documents")
        self.instructions_button.setMaximumHeight(30)
        self._update_instructions_button_style()
        self.instructions_button.clicked.connect(self.on_instructions_clicked)
        bottom_buttons_layout.addWidget(self.instructions_button)
        
        # Resume button - small and unobtrusive
        self.resume_button = QPushButton("📂 Resume Incomplete Workflow")
        self.resume_button.setMaximumHeight(30)
        self._update_resume_button_style()
        self.resume_button.clicked.connect(self.on_resume_clicked)
        bottom_buttons_layout.addWidget(self.resume_button)
        
        # Check for Updates button
        self.update_button = QPushButton("🔄 Check for Updates")
        self.update_button.setMaximumHeight(30)
        self._update_update_button_style()
        self.update_button.clicked.connect(self.on_check_updates_clicked)
        bottom_buttons_layout.addWidget(self.update_button)
        
        layout.addLayout(bottom_buttons_layout)
        
        self.setLayout(layout)
    
    def _update_resume_button_style(self):
        """Apply theme-aware style to the resume button."""
        if theme_manager.dark_mode:
            self.resume_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #AAAAAA;
                    border: 1px solid #AAAAAA;
                    border-radius: 3px;
                    padding: 5px 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #3A3A3A;
                    color: #E0E0E0;
                    border-color: #E0E0E0;
                }
            """)
        else:
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

    def _update_update_button_style(self):
        """Apply theme-aware style to the update button."""
        if theme_manager.dark_mode:
            self.update_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #AAAAAA;
                    border: 1px solid #AAAAAA;
                    border-radius: 3px;
                    padding: 5px 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #3A3A3A;
                    color: #E0E0E0;
                    border-color: #E0E0E0;
                }
            """)
        else:
            self.update_button.setStyleSheet("""
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

    def _update_instructions_button_style(self):
        """Apply theme-aware style to the instructions button."""
        if theme_manager.dark_mode:
            self.instructions_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #AAAAAA;
                    border: 1px solid #AAAAAA;
                    border-radius: 3px;
                    padding: 5px 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #3A3A3A;
                    color: #E0E0E0;
                    border-color: #E0E0E0;
                }
            """)
        else:
            self.instructions_button.setStyleSheet("""
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

    def _get_item_style(self, selected=False):
        """Get theme-aware style for resume dialog list items."""
        dark = theme_manager.dark_mode
        if selected:
            return """
                QWidget {
                    background-color: #2E4A2E;
                    border: 2px solid #77C25E;
                    border-radius: 3px;
                    padding: 10px;
                }
            """ if dark else """
                QWidget {
                    background-color: #e8f5e9;
                    border: 2px solid #77C25E;
                    border-radius: 3px;
                    padding: 10px;
                }
            """
        return ("""
            QWidget {
                background-color: #2D2D2D;
                border: 1px solid #3A3A3A;
                border-radius: 3px;
                padding: 10px;
            }
            QWidget:hover {
                background-color: #3A3A3A;
            }
        """ if dark else """
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
    
    def on_view_reports_clicked(self):
        """Open the reports folder in file explorer."""
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   "output", "reports")
        
        # Create directory if it doesn't exist
        os.makedirs(reports_dir, exist_ok=True)
        
        # Open in file explorer (cross-platform)
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(reports_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", reports_dir])
            else:  # Linux
                subprocess.Popen(["xdg-open", reports_dir])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open reports folder:\n{str(e)}")
    
    def on_instructions_clicked(self):
        """Open workflow picker dialog and generate instruction PDF."""
        loader = WorkflowLoader()
        qc_workflows = loader.get_qc_workflows()
        maint_workflows = loader.get_maintenance_workflows()
        
        if not qc_workflows and not maint_workflows:
            QMessageBox.information(self, "No Workflows", 
                "No workflows found. Create workflows in Mode 2 or Mode 3 first.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Workflow Instruction Documents")
        dialog.setMinimumSize(450, 400)
        dlayout = QVBoxLayout(dialog)
        
        dlayout.addWidget(QLabel("Select a workflow to generate a printable instruction document:"))
        
        workflow_list = QListWidget()
        workflow_map = {}  # list index -> workflow dict
        
        if qc_workflows:
            header = QListWidgetItem("── QC Workflows ──")
            header.setFlags(Qt.NoItemFlags)
            header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            workflow_list.addItem(header)
            for wf in qc_workflows:
                name = wf.get('name', os.path.basename(wf.get('_file_path', 'Unknown')))
                desc = wf.get('description', '')
                steps = len(wf.get('steps', []))
                item = QListWidgetItem(f"  {name}  ({steps} steps)")
                if desc:
                    item.setToolTip(desc)
                workflow_list.addItem(item)
                workflow_map[workflow_list.count() - 1] = wf
        
        if maint_workflows:
            header = QListWidgetItem("── Maintenance Workflows ──")
            header.setFlags(Qt.NoItemFlags)
            header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            workflow_list.addItem(header)
            for wf in maint_workflows:
                name = wf.get('name', os.path.basename(wf.get('_file_path', 'Unknown')))
                desc = wf.get('description', '')
                steps = len(wf.get('steps', []))
                item = QListWidgetItem(f"  {name}  ({steps} steps)")
                if desc:
                    item.setToolTip(desc)
                workflow_list.addItem(item)
                workflow_map[workflow_list.count() - 1] = wf
        
        dlayout.addWidget(workflow_list)
        
        btn_layout = QHBoxLayout()
        generate_btn = QPushButton("Generate PDF")
        generate_btn.setEnabled(False)
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #77C25E; color: white; padding: 8px 20px;
                border-radius: 3px; font-weight: bold;
            }
            QPushButton:hover { background-color: #5FA84A; }
            QPushButton:disabled { background-color: #CCCCCC; color: #666666; }
        """)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #888888; color: white; padding: 8px 20px;
                border-radius: 3px; font-weight: bold;
            }
            QPushButton:hover { background-color: #666666; }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(generate_btn)
        btn_layout.addWidget(cancel_btn)
        dlayout.addLayout(btn_layout)
        
        def on_selection_changed():
            row = workflow_list.currentRow()
            generate_btn.setEnabled(row in workflow_map)
        
        def on_generate():
            row = workflow_list.currentRow()
            wf = workflow_map.get(row)
            if not wf:
                return
            dialog.accept()
            
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                       "output", "reports")
            pdf_path = generate_workflow_instructions(wf, output_dir)
            if pdf_path and os.path.exists(pdf_path):
                import subprocess, platform
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
        
        workflow_list.currentRowChanged.connect(on_selection_changed)
        workflow_list.itemDoubleClicked.connect(lambda: on_generate() if workflow_list.currentRow() in workflow_map else None)
        generate_btn.clicked.connect(on_generate)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()
    
    def on_check_updates_clicked(self):
        """Check for application updates via git."""
        import subprocess
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        def run_git(*args):
            result = subprocess.run(["git"] + list(args), cwd=app_dir,
                                    capture_output=True, text=True, timeout=30)
            return result
        
        try:
            # Check if git is available
            if subprocess.run(["git", "--version"], capture_output=True).returncode != 0:
                QMessageBox.warning(self, "Git Not Found",
                    "Git is not installed. Please install Git to use automatic updates.")
                return
            
            # Check if this is a git repo
            if run_git("rev-parse", "--git-dir").returncode != 0:
                QMessageBox.information(self, "Not a Git Repository",
                    "This installation was not set up with Git.\n\n"
                    "To enable automatic updates, clone the repository:\n"
                    "  git clone https://github.com/cragand/emtech-eoat-workbench-wizard.git\n\n"
                    "See the README for full installation instructions.")
                return
            
            # Fetch latest
            self.update_button.setText("🔄 Checking...")
            self.update_button.setEnabled(False)
            QApplication.processEvents()
            
            if run_git("fetch", "origin").returncode != 0:
                QMessageBox.warning(self, "Connection Error",
                    "Could not connect to the update server.\n\n"
                    "Check your internet connection and try again.")
                return
            
            # Check for updates
            diff = run_git("diff", "--quiet", "HEAD", "origin/main")
            if diff.returncode == 0:
                current = run_git("log", "-1", "--format=%h (%ci)")
                QMessageBox.information(self, "Up to Date",
                    f"You are running the latest version.\n\n"
                    f"Current: {current.stdout.strip()}")
                return
            
            # Show available changes
            changes = run_git("log", "HEAD..origin/main", "--format=• %s")
            reply = QMessageBox.question(self, "Updates Available",
                f"Updates are available:\n\n{changes.stdout.strip()}\n\n"
                "Apply updates now? The application will restart.",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply != QMessageBox.Yes:
                return
            
            # Pull updates
            pull = run_git("pull", "origin", "main")
            if pull.returncode != 0:
                QMessageBox.warning(self, "Update Failed",
                    "Update failed. This can happen if files were manually edited.\n\n"
                    f"{pull.stderr.strip()}")
                return
            
            # Update dependencies
            import sys
            import platform
            venv_pip = os.path.join(app_dir, "venv",
                "Scripts" if platform.system() == "Windows" else "bin", "pip")
            if os.path.exists(venv_pip):
                subprocess.run([venv_pip, "install", "-r",
                    os.path.join(app_dir, "requirements.txt"), "--quiet"],
                    cwd=app_dir, capture_output=True)
            
            QMessageBox.information(self, "Update Complete",
                "Update applied successfully!\n\n"
                "Please restart the application for changes to take effect.")
            
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Timeout",
                "Update check timed out. Check your network connection.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Update check failed:\n{str(e)}")
        finally:
            self.update_button.setText("🔄 Check for Updates")
            self.update_button.setEnabled(True)

    def open_camera_settings(self):
        """Open camera settings dialog."""
        dialog = CameraSettingsDialog(parent=self)
        dialog.exec_()
    
    def on_usb_barcode_scanned(self, barcode_data):
        """Handle barcode from USB HID scanner - populate serial number field."""
        self.serial_input.setText(barcode_data)
        self.serial_input.setFocus()
    
    def open_serial_scan_dialog(self):
        """Open dialog to scan barcode for serial number."""
        if not QR_SCANNER_AVAILABLE:
            QMessageBox.information(self, "Scanner Unavailable",
                                   "Barcode scanner not available. Please install pyzbar library.")
            return
        
        dialog = SerialScanDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            scanned_data = dialog.get_scanned_data()
            if scanned_data:
                self.serial_input.setText(scanned_data)
    
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
            item_widget.setStyleSheet(self._get_item_style())
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
                        w.setStyleSheet(self._get_item_style())
                item_widget.setStyleSheet(self._get_item_style(selected=True))
            
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



class SerialScanDialog(QDialog):
    """Dialog for scanning barcode to populate serial number."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan Serial Number")
        self.setModal(True)
        self.resize(800, 650)
        
        self.camera = None
        self.scanner = None
        self.available_cameras = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.scanned_data = None
        
        self.init_ui()
        self.discover_cameras()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Select camera and point at barcode/QR code, then click Scan when button is enabled")
        instructions.setStyleSheet("font-size: 12px; padding: 10px;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Camera selection
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Camera:")
        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo)
        
        # Camera settings button
        self.camera_settings_button = QPushButton("⚙️ Settings")
        self.camera_settings_button.setMaximumWidth(100)
        self.camera_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.camera_settings_button.clicked.connect(self.open_camera_settings)
        camera_layout.addWidget(self.camera_settings_button)
        
        camera_layout.addStretch()
        layout.addLayout(camera_layout)
        
        # Camera preview
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px solid black; background-color: #2b2b2b;")
        self.preview_label.setMinimumSize(640, 480)
        layout.addWidget(self.preview_label)
        
        # Status label
        self.status_label = QLabel("Select a camera to begin...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("Scan")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setEnabled(False)
        self.scan_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.scan_button.clicked.connect(self.on_scan_clicked)
        button_layout.addWidget(self.scan_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumHeight(40)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def discover_cameras(self):
        """Discover available cameras."""
        self.status_label.setText("Discovering cameras...")
        try:
            cameras = CameraManager.discover_cameras()
            
            # Close all cameras after discovery
            for cam in cameras:
                cam.close()
            
            self.available_cameras = cameras
            
            if cameras:
                for cam in cameras:
                    self.camera_combo.addItem(cam.name)
                self.status_label.setText(f"Found {len(cameras)} camera(s)")
            else:
                self.status_label.setText("No cameras found")
                self.camera_combo.addItem("No cameras available")
        except Exception as e:
            self.status_label.setText(f"Error discovering cameras: {str(e)}")
    
    def on_camera_changed(self, index):
        """Handle camera selection change."""
        try:
            self.timer.stop()
            
            if self.scanner:
                self.scanner.stop()
                self.scanner = None
            
            if hasattr(self, 'scan_check_timer') and self.scan_check_timer:
                self.scan_check_timer.stop()
            
            if self.camera:
                self.camera.close()
                self.camera = None
            
            if index >= 0 and index < len(self.available_cameras):
                self.camera = self.available_cameras[index]
                
                if self.camera.open():
                    self.timer.start(30)
                    self.status_label.setText("Camera ready - waiting for barcode...")
                    self.scan_button.setEnabled(False)
                    
                    # Start scanner
                    self.scanner = QRScannerThread()
                    self.scanner.barcode_detected.connect(self.on_barcode_detected)
                    self.scanner.start()
                    
                    # Check scanner state
                    self.scan_check_timer = QTimer()
                    self.scan_check_timer.timeout.connect(self.update_scan_button)
                    self.scan_check_timer.start(100)
                else:
                    self.status_label.setText("Failed to open camera")
        except Exception as e:
            self.status_label.setText(f"Camera error: {str(e)}")
    
    def update_frame(self):
        """Update camera preview."""
        if not self.camera:
            return
        
        frame = self.camera.capture_frame()
        if frame is not None:
            # Feed frame to QR scanner (thread-safe)
            if self.scanner:
                self.scanner.update_frame(frame)
            
            # Convert to QImage
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            q_img = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Scale to fit preview
            pixmap = QPixmap.fromImage(q_img)
            scaled_pixmap = pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
            self.preview_label.setPixmap(scaled_pixmap)
    
    def on_barcode_detected(self, barcode_type, barcode_data):
        """Handle barcode detection."""
        self.status_label.setText(f"Detected: {barcode_type} - {barcode_data}")
    
    def update_scan_button(self):
        """Enable/disable scan button based on detection."""
        if self.scanner:
            barcode_type, barcode_data = self.scanner.get_current_barcode()
            self.scan_button.setEnabled(barcode_type is not None)
    
    def on_scan_clicked(self):
        """Handle scan button click."""
        if self.scanner:
            barcode_type, barcode_data = self.scanner.get_current_barcode()
            if barcode_data:
                self.scanned_data = barcode_data
                self.accept()
    
    def open_camera_settings(self):
        """Open camera settings dialog."""
        dialog = CameraSettingsDialog(self.available_cameras, parent=self)
        dialog.exec_()
    
    def get_scanned_data(self):
        """Get the scanned barcode data."""
        return self.scanned_data
    
    def closeEvent(self, event):
        """Clean up on close."""
        if self.timer.isActive():
            self.timer.stop()
        
        if hasattr(self, 'scan_check_timer') and self.scan_check_timer.isActive():
            self.scan_check_timer.stop()
        
        if self.scanner:
            self.scanner.stop()
            self.scanner = None
        
        if self.camera:
            self.camera.close()
            self.camera = None
        
        event.accept()
