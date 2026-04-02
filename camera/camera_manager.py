"""Camera manager for discovering and managing multiple cameras."""
from typing import List, Optional
from .camera_interface import CameraInterface
from .opencv_camera import OpenCVCamera
from .camera_config_manager import CameraConfigManager
from logger_config import get_logger

logger = get_logger(__name__)


class CameraManager:
    """Manages camera discovery and access."""

    @staticmethod
    def discover_cameras() -> List[CameraInterface]:
        """Discover all available cameras.
        
        Probes up to max_camera_index indices (from user preferences,
        default 8). Each camera is closed after verification to avoid
        holding USB resources that block subsequent probes. Stops early
        after 4 consecutive failures to keep startup fast when fewer
        cameras are connected.
        """
        from preferences_manager import preferences

        max_index = preferences.get("max_camera_index") or 8
        cameras = []
        consecutive_failures = 0
        
        for i in range(max_index):
            cam = OpenCVCamera(i)
            if cam.open():
                consecutive_failures = 0
                logger.info(f"Discovered camera at index {i}: {cam.name}")
                # Close immediately so we don't hold USB resources
                # that could block discovery of remaining cameras
                cam.close()
                cameras.append(cam)
            else:
                cam.close()
                consecutive_failures += 1
                if consecutive_failures >= 4:
                    logger.debug(f"Stopping camera discovery after 4 consecutive failures at index {i}")
                    break
        
        return cameras
    
    @staticmethod
    def get_camera_by_type(camera_type: str, index: int = 0) -> Optional[CameraInterface]:
        """Get a specific camera by type."""
        return OpenCVCamera(index)
