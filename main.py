"""Main application entry point."""
import sys
import os
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox, QPushButton, QHBoxLayout, QWidget
from PyQt5.QtCore import Qt
from gui import ModeSelectionScreen, Mode1CaptureScreen
from gui.workflow_selection import WorkflowSelectionScreen
from gui.workflow_execution import WorkflowExecutionScreen
from gui.workflow_editor import WorkflowEditorScreen
from theme_manager import theme_manager
from logger_config import setup_logging, get_logger

logger = get_logger(__name__)

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emtech EoAT Workbench Wizard")
        self.setMinimumSize(1024, 850)
        
        # Store serial number and description for workflow modes
        self.current_serial = None
        self.current_description = None
        
        # Create central widget with layout for stack and theme button
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        from PyQt5.QtWidgets import QVBoxLayout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Theme toggle button at top
        theme_bar = QWidget()
        theme_bar.setMaximumHeight(40)
        theme_layout = QHBoxLayout(theme_bar)
        theme_layout.setContentsMargins(10, 5, 10, 5)
        theme_layout.addStretch()
        
        self.theme_button = QPushButton("🌙 Dark Mode")
        self.theme_button.setMinimumWidth(130)
        self.theme_button.setFocusPolicy(Qt.NoFocus)  # Prevent spacebar from triggering
        self.theme_button.clicked.connect(self.toggle_theme)
        theme_layout.addWidget(self.theme_button)
        
        main_layout.addWidget(theme_bar)
        
        # Stacked widget for switching between screens
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # Mode selection screen
        self.mode_selection = ModeSelectionScreen()
        self.mode_selection.mode_selected.connect(self.on_mode_selected)
        self.mode_selection.resume_workflow.connect(self.on_resume_workflow)
        self.stack.addWidget(self.mode_selection)
        
        self.current_mode_widget = None
    
    def on_resume_workflow(self, workflow_path: str, serial_number: str, technician: str):
        """Handle resuming an incomplete workflow."""
        logger.info(f"Resuming workflow: {workflow_path} for serial: {serial_number}")
        
        # Store for workflow
        self.current_serial = serial_number
        self.current_technician = technician
        self.current_description = ""  # Will be loaded from progress file
        
        # Remove previous mode widget if exists
        if self.current_mode_widget:
            self.stack.removeWidget(self.current_mode_widget)
            self.current_mode_widget.deleteLater()
            self.current_mode_widget = None
        
        # Create workflow execution screen
        self.current_mode_widget = WorkflowExecutionScreen(
            workflow_path,
            serial_number,
            technician,
            self.current_description
        )
        self.current_mode_widget.back_requested.connect(self.return_to_mode_selection)
        
        self.stack.addWidget(self.current_mode_widget)
        self.stack.setCurrentWidget(self.current_mode_widget)
    
    def on_mode_selected(self, mode: int, serial_number: str, technician: str, description: str):
        """Handle mode selection."""
        # Store for workflow modes
        self.current_serial = serial_number
        self.current_technician = technician
        self.current_description = description
        
        # Remove previous mode widget if exists
        if self.current_mode_widget:
            self.stack.removeWidget(self.current_mode_widget)
            self.current_mode_widget.deleteLater()
            self.current_mode_widget = None
        
        # Create appropriate mode widget
        if mode == 1:
            self.current_mode_widget = Mode1CaptureScreen(serial_number, technician, description)
            self.current_mode_widget.back_requested.connect(self.return_to_mode_selection)
        elif mode == 2:
            # Show workflow selection for QC
            workflow_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                       "workflows", "qc_workflows")
            self.current_mode_widget = WorkflowSelectionScreen(2, workflow_dir)
            self.current_mode_widget.workflow_selected.connect(self.on_workflow_selected)
            self.current_mode_widget.edit_workflows.connect(self.on_edit_workflows)
            self.current_mode_widget.back_requested.connect(self.return_to_mode_selection)
        elif mode == 3:
            # Show workflow selection for Maintenance
            workflow_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                       "workflows", "maintenance_workflows")
            self.current_mode_widget = WorkflowSelectionScreen(3, workflow_dir)
            self.current_mode_widget.workflow_selected.connect(self.on_workflow_selected)
            self.current_mode_widget.edit_workflows.connect(self.on_edit_workflows)
            self.current_mode_widget.back_requested.connect(self.return_to_mode_selection)
        
        if self.current_mode_widget:
            self.stack.addWidget(self.current_mode_widget)
            self.stack.setCurrentWidget(self.current_mode_widget)
    
    def on_workflow_selected(self, workflow_path):
        """Handle workflow selection - start workflow execution."""
        # Remove workflow selection screen
        if self.current_mode_widget:
            self.stack.removeWidget(self.current_mode_widget)
            self.current_mode_widget.deleteLater()
        
        # Create workflow execution screen
        self.current_mode_widget = WorkflowExecutionScreen(
            workflow_path, 
            self.current_serial,
            self.current_technician,
            self.current_description
        )
        self.current_mode_widget.back_requested.connect(self.return_to_mode_selection)
        
        self.stack.addWidget(self.current_mode_widget)
        self.stack.setCurrentWidget(self.current_mode_widget)
    
    def toggle_theme(self):
        """Toggle between light and dark mode."""
        stylesheet = theme_manager.toggle_theme()
        QApplication.instance().setStyleSheet(stylesheet)
        
        # Update button text
        if theme_manager.dark_mode:
            self.theme_button.setText("☀️ Light Mode")
        else:
            self.theme_button.setText("🌙 Dark Mode")
    
    def on_edit_workflows(self):
        """Handle edit workflows request."""
        # Get the workflow directory from current mode widget
        if isinstance(self.current_mode_widget, WorkflowSelectionScreen):
            workflow_dir = self.current_mode_widget.workflow_dir
            mode_number = self.current_mode_widget.mode_number
            
            # Remove workflow selection screen
            self.stack.removeWidget(self.current_mode_widget)
            self.current_mode_widget.deleteLater()
            
            # Create workflow editor screen
            self.current_mode_widget = WorkflowEditorScreen(mode_number, workflow_dir)
            self.current_mode_widget.back_requested.connect(self.return_to_mode_selection)
            
            self.stack.addWidget(self.current_mode_widget)
            self.stack.setCurrentWidget(self.current_mode_widget)
    
    def return_to_mode_selection(self):
        """Return to mode selection screen."""
        # Switch to mode selection screen
        self.stack.setCurrentWidget(self.mode_selection)
        
        # Clean up the mode widget
        if self.current_mode_widget:
            self.stack.removeWidget(self.current_mode_widget)
            self.current_mode_widget.deleteLater()
            self.current_mode_widget = None


def main():
    """Application entry point."""
    # Initialize logging first
    setup_logging()
    logger.info("Starting Camera QC Application")
    
    try:
        app = QApplication(sys.argv)
        
        # Apply initial theme (light mode)
        app.setStyleSheet(theme_manager.get_stylesheet())
        
        window = MainWindow()
        window.show()
        
        logger.info("Application window displayed successfully")
        sys.exit(app.exec_())
    except Exception as e:
        logger.exception("Fatal error during application startup")
        QMessageBox.critical(None, "Startup Error", 
                           f"Failed to start application:\n{str(e)}\n\nCheck logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
