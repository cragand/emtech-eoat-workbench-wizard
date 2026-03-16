"""Passive barcode/QR code scanner that runs in background."""
import cv2
import threading
from PyQt5.QtCore import QThread, pyqtSignal


class QRScannerThread(QThread):
    """Background thread for passive barcode/QR code scanning.
    
    Uses a shared frame buffer instead of reading from the camera directly,
    to avoid thread-safety issues with OpenCV VideoCapture.
    """
    
    barcode_detected = pyqtSignal(str, str)  # Emits (barcode_type, data) when detected
    
    def __init__(self, camera=None):
        super().__init__()
        self.running = False
        self.last_barcode_data = None
        self.current_barcode_type = None
        self.current_barcode_data = None
        self._frame = None
        self._frame_lock = threading.Lock()
    
    def update_frame(self, frame):
        """Called by the main thread to provide the latest camera frame."""
        with self._frame_lock:
            self._frame = frame.copy() if frame is not None else None
    
    def run(self):
        """Run barcode scanning loop."""
        self.running = True
        
        try:
            from pyzbar import pyzbar
        except ImportError:
            print("pyzbar not available, barcode scanning disabled")
            return
        
        while self.running:
            try:
                with self._frame_lock:
                    frame = self._frame
                
                if frame is None or not self.running:
                    self.msleep(100)
                    continue
                
                # Decode barcodes
                decoded_objects = pyzbar.decode(frame)
                
                if decoded_objects:
                    obj = decoded_objects[0]
                    barcode_type = obj.type
                    barcode_data = obj.data.decode('utf-8')
                    
                    self.current_barcode_type = barcode_type
                    self.current_barcode_data = barcode_data
                    
                    if barcode_data != self.last_barcode_data:
                        self.last_barcode_data = barcode_data
                        self.barcode_detected.emit(barcode_type, barcode_data)
                else:
                    self.current_barcode_type = None
                    self.current_barcode_data = None
                
                self.msleep(100)
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
        if not self.wait(2000):
            print("QR scanner thread did not stop in time, abandoning")
