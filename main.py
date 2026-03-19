"""Main application entry point."""
import sys
import os
import math
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QMessageBox, 
                             QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush
from gui import ModeSelectionScreen, Mode1CaptureScreen
from gui.workflow_selection import WorkflowSelectionScreen
from gui.workflow_execution import WorkflowExecutionScreen
from gui.workflow_editor import WorkflowEditorScreen
from theme_manager import theme_manager
from logger_config import setup_logging, get_logger
from usb_barcode_scanner import USBBarcodeScanner

logger = get_logger(__name__)


class CameraDiscoveryThread(QThread):
    """Discovers cameras in a background thread."""
    cameras_found = pyqtSignal(list)
    
    def run(self):
        from camera import CameraManager
        cameras = CameraManager.discover_cameras()
        self.cameras_found.emit(cameras)


class GearSpinnerWidget(QWidget):
    """Animated spinning gear widget."""
    
    def __init__(self, size=80, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._size = size
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(30)
    
    def _rotate(self):
        self._angle = (self._angle + 3) % 360
        self.update()
    
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(self._size / 2, self._size / 2)
        p.rotate(self._angle)
        
        r = self._size * 0.4  # outer radius
        ir = r * 0.55  # inner radius (tooth valley)
        hr = r * 0.3  # center hole radius
        teeth = 8
        
        # Build gear path
        path = QPainterPath()
        for i in range(teeth):
            a1 = math.radians(i * 360 / teeth - 360 / teeth / 4)
            a2 = math.radians(i * 360 / teeth + 360 / teeth / 4)
            a3 = math.radians((i + 0.5) * 360 / teeth - 360 / teeth / 4)
            a4 = math.radians((i + 0.5) * 360 / teeth + 360 / teeth / 4)
            
            if i == 0:
                path.moveTo(r * math.cos(a1), r * math.sin(a1))
            else:
                path.lineTo(r * math.cos(a1), r * math.sin(a1))
            path.lineTo(r * math.cos(a2), r * math.sin(a2))
            path.lineTo(ir * math.cos(a3), ir * math.sin(a3))
            path.lineTo(ir * math.cos(a4), ir * math.sin(a4))
        path.closeSubpath()
        
        # Cut center hole
        hole = QPainterPath()
        hole.addEllipse(QPointF(0, 0), hr, hr)
        path = path.subtracted(hole)
        
        p.setPen(QPen(QColor("#5FA84A"), 1.5))
        p.setBrush(QBrush(QColor("#77C25E")))
        p.drawPath(path)
        p.end()
    
    def stop(self):
        self._timer.stop()


class CameraDiscoveryDialog(QDialog):
    """Modal overlay shown during camera discovery."""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.gear = GearSpinnerWidget(80, self)
        layout.addWidget(self.gear, alignment=Qt.AlignCenter)
        
        label = QLabel("Discovering cameras...")
        label.setStyleSheet("color: #77C25E; font-size: 16px; font-weight: bold; background: transparent;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        self.setFixedSize(250, 160)
    
    def showEvent(self, event):
        # Center on parent
        if self.parent():
            pr = self.parent().geometry()
            self.move(pr.center() - self.rect().center())
        super().showEvent(event)
    
    def closeEvent(self, event):
        self.gear.stop()
        super().closeEvent(event)

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emtech EoAT Workbench Wizard")
        self.setMinimumSize(1024, 850)
        
        # Store serial number and description for workflow modes
        self.current_serial = None
        self.current_description = None
        
        # Cache discovered cameras (shared across all screens)
        self.cached_cameras = None
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
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
        
        # USB HID barcode scanner (global interceptor)
        self.usb_barcode_scanner = USBBarcodeScanner(self)
        self.usb_barcode_scanner.barcode_scanned.connect(self.on_usb_barcode)
    
    def on_usb_barcode(self, barcode_data):
        """Route USB barcode scan to the active screen."""
        current = self.stack.currentWidget()
        if hasattr(current, 'on_usb_barcode_scanned'):
            current.on_usb_barcode_scanned(barcode_data)
    
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
        
        # Create workflow execution screen with cached cameras
        self.current_mode_widget = WorkflowExecutionScreen(
            workflow_path,
            serial_number,
            technician,
            self.current_description,
            cached_cameras=self.cached_cameras
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
            self.current_description,
            cached_cameras=self.cached_cameras
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
        
        # Refresh widgets with inline styles
        self.mode_selection._update_resume_button_style()
        self.mode_selection._update_update_button_style()
        self.mode_selection._update_instructions_button_style()
    
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
    setup_logging()
    logger.info("Starting Camera QC Application")

    # Global exception hook — log crashes that would otherwise be silent
    def _unhandled_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _unhandled_exception
    
    try:
        app = QApplication(sys.argv)
        app.setStyleSheet(theme_manager.get_stylesheet())
        
        window = MainWindow()
        window.show()
        
        # Discover cameras in background thread with spinner
        discovery_dialog = CameraDiscoveryDialog(window)
        discovery_thread = CameraDiscoveryThread()
        
        def on_cameras_found(cameras):
            window.cached_cameras = cameras
            logger.info(f"Found {len(cameras)} camera(s)")
            discovery_dialog.close()
        
        discovery_thread.cameras_found.connect(on_cameras_found)
        discovery_thread.start()
        discovery_dialog.exec_()
        
        logger.info("Application window displayed successfully")
        sys.exit(app.exec_())
    except Exception as e:
        logger.exception("Fatal error during application startup")
        QMessageBox.critical(None, "Startup Error", 
                           f"Failed to start application:\n{str(e)}\n\nCheck logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
