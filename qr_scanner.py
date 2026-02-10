"""Passive QR code scanner that runs in background."""
import cv2
from PyQt5.QtCore import QThread, pyqtSignal


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
        
        # Try to import pyzbar, skip if not available
        try:
            from pyzbar import pyzbar
        except ImportError:
            print("pyzbar not available, QR scanning disabled")
            return
        
        while self.running:
            try:
                if not self.camera or not self.running:
                    break
                
                frame = self.camera.capture_frame()
                if frame is None or not self.running:
                    self.msleep(100)
                    continue
                
                # Decode QR codes
                decoded_objects = pyzbar.decode(frame)
                
                for obj in decoded_objects:
                    if not self.running:
                        break
                    qr_data = obj.data.decode('utf-8')
                    # Only emit if it's a new QR code
                    if qr_data != self.last_qr_data:
                        self.last_qr_data = qr_data
                        self.qr_detected.emit(qr_data)
                
                self.msleep(100)  # Check every 100ms
            except Exception as e:
                print(f"QR scanner error: {e}")
                if not self.running:
                    break
                self.msleep(100)
    
    def stop(self):
        """Stop the scanner thread."""
        self.running = False
        self.camera = None  # Release camera reference immediately
        
        # Don't wait forever - give it 500ms then force quit
        if not self.wait(500):
            print("QR scanner thread timeout, terminating...")
            self.terminate()
            self.wait(100)
