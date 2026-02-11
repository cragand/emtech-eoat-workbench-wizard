"""Main application entry point."""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from gui import ModeSelectionScreen, Mode1CaptureScreen


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
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
            # TODO: Implement Mode 2
            print(f"Mode 2 not yet implemented. Serial: {serial_number}, Desc: {description}")
            return
        elif mode == 3:
            # TODO: Implement Mode 3
            print(f"Mode 3 not yet implemented. Serial: {serial_number}, Desc: {description}")
            return
        
        if self.current_mode_widget:
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
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
