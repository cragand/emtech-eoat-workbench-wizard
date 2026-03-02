"""OpenCV-based camera implementation for webcams and USB cameras."""
import cv2
import numpy as np
import platform
from typing import Optional, Tuple
from .camera_interface import CameraInterface


class OpenCVCamera(CameraInterface):
    """Camera implementation using OpenCV (for webcams and borescope)."""
    
    def __init__(self, camera_index: int = 0):
        super().__init__(f"opencv_{camera_index}")
        self.camera_index = camera_index
        self.capture = None
        self._detected_name = None
    
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
        else:
            # Try to detect camera name
            self._detect_camera_name()
            
        return self.is_open
    
    def _detect_camera_name(self):
        """Attempt to detect the actual camera name."""
        try:
            # Try to get backend name
            backend = self.capture.getBackendName()
            
            # On Windows with DirectShow, try to get device name
            if platform.system() == "Windows":
                try:
                    import subprocess
                    # Use PowerShell to get camera names
                    result = subprocess.run(
                        ['powershell', '-Command', 
                         'Get-PnpDevice -Class Camera | Select-Object -ExpandProperty FriendlyName'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    
                    if result.returncode == 0:
                        camera_names = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
                        if camera_names and self.camera_index < len(camera_names):
                            self._detected_name = camera_names[self.camera_index]
                            return
                except:
                    pass
            
            # Fallback: Try to detect based on resolution and capabilities
            width, height = self.get_resolution()
            
            # Common patterns
            if width == 1280 and height == 720:
                self._detected_name = f"HD Webcam (Camera {self.camera_index})"
            elif width == 1920 and height == 1080:
                self._detected_name = f"Full HD Webcam (Camera {self.camera_index})"
            elif width == 640 and height == 480:
                self._detected_name = f"VGA Camera (Camera {self.camera_index})"
            else:
                self._detected_name = f"Camera {self.camera_index} ({width}x{height})"
                
        except:
            pass
    
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
        if not ret or frame is None:
            return None
        
        # Handle different color formats
        if len(frame.shape) == 2:
            # Grayscale image - convert to BGR for consistency
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif len(frame.shape) == 3 and frame.shape[2] == 4:
            # BGRA - convert to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        # Otherwise assume it's already BGR (most common case)
        
        return frame
    
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
        if self._detected_name:
            return self._detected_name
        return f"Camera {self.camera_index}"
