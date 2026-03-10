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
        """Best-effort camera name lookup on Windows. Non-blocking with short timeout."""
        if platform.system() != "Windows":
            return []
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 "Get-PnpDevice -Status OK -Class Camera | "
                 "Select-Object -ExpandProperty FriendlyName"],
                capture_output=True, text=True, timeout=3
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
        """
        cameras = []
        
        # Get device names once (best-effort, won't block long)
        device_names = CameraManager._get_windows_camera_names()
        
        for i in range(3):
            cam = OpenCVCamera(i)
            if cam.open():
                # Assign name if available, otherwise keeps default "Camera N"
                if i < len(device_names):
                    cam._detected_name = device_names[i]
                
                # Apply optimal settings
                try:
                    CameraConfigManager.initialize_camera_with_optimal_settings(
                        cam.capture, cam.name)
                except Exception as e:
                    print(f"Warning: Could not apply optimal settings to {cam.name}: {e}")
                
                cameras.append(cam)
            else:
                cam.close()
                break
        
        return cameras
    
    @staticmethod
    def get_camera_by_type(camera_type: str, index: int = 0) -> Optional[CameraInterface]:
        """Get a specific camera by type."""
        return OpenCVCamera(index)
