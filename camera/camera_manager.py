"""Camera manager for discovering and managing multiple cameras."""
from typing import List, Optional
from .camera_interface import CameraInterface
from .opencv_camera import OpenCVCamera
from .camera_config_manager import CameraConfigManager


class CameraManager:
    """Manages camera discovery and access."""

    @staticmethod
    def discover_cameras() -> List[CameraInterface]:
        """Discover all available cameras.
        
        Optimized for fast discovery - only checks first 3 indices
        and stops immediately when a camera fails to open.
        """
        cameras = []
        
        for i in range(3):
            cam = OpenCVCamera(i)
            if cam.open():
                # Apply saved settings (no probing)
                try:
                    CameraConfigManager.initialize_camera_with_optimal_settings(
                        cam.capture, cam.name)
                except Exception as e:
                    print(f"Warning: Could not apply settings to {cam.name}: {e}")
                
                cameras.append(cam)
            else:
                cam.close()
                break
        
        return cameras
    
    @staticmethod
    def get_camera_by_type(camera_type: str, index: int = 0) -> Optional[CameraInterface]:
        """Get a specific camera by type."""
        return OpenCVCamera(index)
