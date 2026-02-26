"""Passive barcode/QR code scanner that runs in background."""
import cv2
from PyQt5.QtCore import QThread, pyqtSignal


class QRScannerThread(QThread):
    """Background thread for passive barcode/QR code scanning."""
    
    barcode_detected = pyqtSignal(str, str)  # Emits (barcode_type, data) when detected
    
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.running = False
        self.last_barcode_data = None
        self.current_barcode_type = None
        self.current_barcode_data = None
    
    def run(self):
        """Run barcode scanning loop."""
        self.running = True
        
        # Try to import pyzbar, skip if not available
        try:
            from pyzbar import pyzbar
        except ImportError:
            print("pyzbar not available, barcode scanning disabled")
            return
        
        while self.running:
            try:
                if not self.camera or not self.running:
                    break
                
                frame = self.camera.capture_frame()
                if frame is None or not self.running:
                    self.msleep(100)
                    continue
                
                # Decode barcodes
                decoded_objects = pyzbar.decode(frame)
                
                if decoded_objects:
                    # Use the first detected barcode
                    obj = decoded_objects[0]
                    barcode_type = obj.type
                    barcode_data = obj.data.decode('utf-8')
                    
                    # Store current detection
                    self.current_barcode_type = barcode_type
                    self.current_barcode_data = barcode_data
                    
                    # Only emit if it's a new barcode
                    if barcode_data != self.last_barcode_data:
                        self.last_barcode_data = barcode_data
                        self.barcode_detected.emit(barcode_type, barcode_data)
                else:
                    # No barcode detected, clear current
                    self.current_barcode_type = None
                    self.current_barcode_data = None
                
                self.msleep(100)  # Check every 100ms
            except Exception as e:
                print(f"Barcode scanner error: {e}")
                if not self.running:
                    break
                self.msleep(100)
    
    def get_current_barcode(self):
        """Get currently detected barcode (type, data) or (None, None)."""
        return self.current_barcode_type, self.current_barcode_data
    
    def stop(self):
        """Stop the scanner thread."""
        self.running = False
        self.camera = None  # Release camera reference immediately
        
        # Don't wait forever - give it 500ms then force quit
        if not self.wait(500):
            print("QR scanner thread timeout, terminating...")
            self.terminate()
            self.wait(100)
