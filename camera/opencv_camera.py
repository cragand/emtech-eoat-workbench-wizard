"""OpenCV-based camera implementation for webcams and USB cameras."""
import cv2
import numpy as np
from typing import Optional, Tuple
from .camera_interface import CameraInterface


class OpenCVCamera(CameraInterface):
    """Camera implementation using OpenCV (for webcams and borescope)."""
    
    def __init__(self, camera_index: int = 0):
        super().__init__(f"opencv_{camera_index}")
        self.camera_index = camera_index
        self.capture = None
    
    def open(self) -> bool:
        """Open camera connection."""
        # Use DirectShow backend on Windows for faster initialization
        self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        
        # Quick timeout check - if camera doesn't open in 1 second, it's not available
        if not self.capture.isOpened():
            return False
        
        # Try to read a frame to verify camera actually works
        ret, _ = self.capture.read()
        self.is_open = ret
        
        if not self.is_open:
            self.capture.release()
            self.capture = None
            
        return self.is_open
    
    def close(self):
        """Close camera connection."""
        if self.capture:
            self.capture.release()
            self.is_open = False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame."""
        if not self.is_open or not self.capture:
            return None
        
        ret, frame = self.capture.read()
        return frame if ret else None
    
    def get_resolution(self) -> Tuple[int, int]:
        """Get current resolution."""
        if not self.capture:
            return (0, 0)
        
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)
    
    def set_resolution(self, width: int, height: int) -> bool:
        """Set resolution."""
        if not self.capture:
            return False
        
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        return True
    
    @property
    def name(self) -> str:
        """Human-readable camera name."""
        return f"USB Camera {self.camera_index}"
