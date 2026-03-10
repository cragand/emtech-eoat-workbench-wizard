"""Camera manager for discovering and managing multiple cameras."""
import platform
import subprocess
from typing import List, Optional
from .camera_interface import CameraInterface
from .opencv_camera import OpenCVCamera
from .camera_config_manager import CameraConfigManager


class CameraManager:
    """Manages camera discovery and access."""
    
    @staticmethod
    def _get_windows_camera_names() -> List[str]:
        """Get camera device names from Windows in DirectShow order."""
        if platform.system() != "Windows":
            return []
        try:
            # Use ffmpeg to list DirectShow devices - this gives names in the
            # exact same order that OpenCV CAP_DSHOW enumerates them
            result = subprocess.run(
                ['ffmpeg', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
                capture_output=True, text=True, timeout=5
            )
            # ffmpeg outputs device list to stderr
            names = []
            lines = result.stderr.split('\n')
            for i, line in enumerate(lines):
                if '"video"' in line.lower() or '(video)' in line.lower():
                    # Extract name from the previous or current line
                    # Format: [dshow @ ...] "Device Name" (video)
                    for part in [line]:
                        start = part.find('"')
                        if start >= 0:
                            end = part.find('"', start + 1)
                            if end > start:
                                names.append(part[start + 1:end])
            if names:
                return names
        except FileNotFoundError:
            pass  # ffmpeg not installed
        except:
            pass
        
        # Fallback: PnpDevice query (order may not match DirectShow)
        try:
            result = subprocess.run(
                ['powershell', '-Command',
                 "Get-PnpDevice -Status OK -Class Camera,Image | "
                 "Select-Object -ExpandProperty FriendlyName"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return [n.strip() for n in result.stdout.strip().split('\n') if n.strip()]
        except:
            pass
        
        return []

    @staticmethod
    def discover_cameras() -> List[CameraInterface]:
        """Discover all available cameras.
        
        Optimized for fast discovery - only checks first 3 indices
        and stops immediately when a camera fails to open.
        Applies optimal settings based on camera type detection.
        """
        cameras = []
        
        # Get device names once before opening cameras
        device_names = CameraManager._get_windows_camera_names()
        
        # Only check first 3 indices - most systems have 1-2 cameras max
        for i in range(3):
            cam = OpenCVCamera(i)
            if cam.open():
                # Assign name from detected list if available
                if i < len(device_names):
                    cam._detected_name = device_names[i]
                
                # Apply optimal settings based on camera type
                try:
                    CameraConfigManager.initialize_camera_with_optimal_settings(
                        cam.capture, 
                        cam.name
                    )
                except Exception as e:
                    print(f"Warning: Could not apply optimal settings to {cam.name}: {e}")
                
                cameras.append(cam)
            else:
                cam.close()
                # Stop immediately when we hit a non-existent camera
                # This prevents checking indices that will timeout
                break
        
        return cameras
    
    @staticmethod
    def get_camera_by_type(camera_type: str, index: int = 0) -> Optional[CameraInterface]:
        """Get a specific camera by type."""
        return OpenCVCamera(index)
