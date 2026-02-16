"""Main application entry point."""
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from gui import ModeSelectionScreen, Mode1CaptureScreen
from gui.workflow_selection import WorkflowSelectionScreen
from gui.workflow_execution import WorkflowExecutionScreen
from gui.workflow_selection import WorkflowSelectionScreen


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emtech EoAT Cam Viewer")
        self.setMinimumSize(1024, 768)
        
        # Store serial number and description for workflow modes
        self.current_serial = None
        self.current_description = None
        super().__init__()
        self.setWindowTitle("Emtech EoAT Cam Viewer")
        self.setMinimumSize(1024, 768)
        
        # Stacked widget for switching between screens
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Mode selection screen
        self.mode_selection = ModeSelectionScreen()
        self.mode_selection.mode_selected.connect(self.on_mode_selected)
        self.stack.addWidget(self.mode_selection)
        
        self.current_mode_widget = None
    
    def on_mode_selected(self, mode: int, serial_number: str, description: str):
        """Handle mode selection."""
        # Store for workflow modes
        self.current_serial = serial_number
        self.current_description = description
        
        # Remove previous mode widget if exists
        if self.current_mode_widget:
            self.stack.removeWidget(self.current_mode_widget)
            self.current_mode_widget.deleteLater()
            self.current_mode_widget = None
        
        # Create appropriate mode widget
        if mode == 1:
            self.current_mode_widget = Mode1CaptureScreen(serial_number, description)
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
            self.current_description
        )
        self.current_mode_widget.back_requested.connect(self.return_to_mode_selection)
        
        self.stack.addWidget(self.current_mode_widget)
        self.stack.setCurrentWidget(self.current_mode_widget)
    
    def on_edit_workflows(self):
        """Handle edit workflows request."""
        # TODO: Create workflow editor screen
        QMessageBox.information(self, "Workflow Editor", 
                               "Workflow editor not yet implemented.")
    
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
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
