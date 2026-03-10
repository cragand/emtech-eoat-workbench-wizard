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
        if platform.system() == "Windows":
            self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        else:
            self.capture = cv2.VideoCapture(self.camera_index)
        
        # Quick timeout check - if camera doesn't open, it's not available
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
            if platform.system() == "Windows":
                try:
                    import subprocess
                    # Enumerate DirectShow video capture devices in the same order
                    # that OpenCV CAP_DSHOW uses, via the SystemDeviceEnum COM object
                    ps_script = (
                        "$devEnum = New-Object -ComObject SystemDeviceEnum; "
                        "$classEnum = $null; "
                        "$catGuid = [Guid]'860BB310-5D01-11D0-BD3B-00A0C911CE86'; "  # VideoInputDevice
                        "[void]$devEnum.CreateClassEnumerator([ref]$catGuid, [ref]$classEnum, 0); "
                        "if ($classEnum) { "
                        "  $moniker = @($null); $fetched = 0; "
                        "  while ($classEnum.Next(1, $moniker, [ref]$fetched) -eq 0) { "
                        "    $bag = $null; "
                        "    $iid = [Guid]'55272A00-42CB-11CE-8135-00AA004BB851'; "
                        "    [void]$moniker[0].BindToStorage($null, $null, [ref]$iid, [ref]$bag); "
                        "    if ($bag) { Write-Output $bag.Read('FriendlyName') } "
                        "  } "
                        "}"
                    )
                    result = subprocess.run(
                        ['powershell', '-Command', ps_script],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        camera_names = [n.strip() for n in result.stdout.strip().split('\n') if n.strip()]
                        if self.camera_index < len(camera_names):
                            self._detected_name = camera_names[self.camera_index]
                            return
                except:
                    pass

            self._detected_name = f"Camera {self.camera_index}"
        except:
            self._detected_name = f"Camera {self.camera_index}"
    
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
        if self._detected_name:
            return self._detected_name
        return f"Camera {self.camera_index}"
