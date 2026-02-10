"""Passive QR code scanner that runs in background."""
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from pyzbar import pyzbar


class QRScannerThread(QThread):
    """Background thread for passive QR code scanning."""
    
    qr_detected = pyqtSignal(str)  # Emits QR code data when detected
    
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.running = False
        self.last_qr_data = None
    
    def run(self):
        """Run QR scanning loop."""
        self.running = True
        while self.running:
            if not self.camera:
                self.msleep(100)
                continue
            
            frame = self.camera.capture_frame()
            if frame is None:
                self.msleep(100)
                continue
            
            # Decode QR codes
            decoded_objects = pyzbar.decode(frame)
            
            for obj in decoded_objects:
                qr_data = obj.data.decode('utf-8')
                # Only emit if it's a new QR code
                if qr_data != self.last_qr_data:
                    self.last_qr_data = qr_data
                    self.qr_detected.emit(qr_data)
            
            self.msleep(100)  # Check every 100ms
    
    def stop(self):
        """Stop the scanner thread."""
        self.running = False
        self.camera = None  # Release camera reference
        self.wait(2000)  # Wait max 2 seconds
        if self.isRunning():
            self.terminate()  # Force terminate if still running
            self.wait()
