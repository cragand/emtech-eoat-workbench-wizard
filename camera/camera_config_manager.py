"""Camera configuration manager with auto-detection of optimal settings."""
import cv2
import json
import os


class CameraConfigManager:
    """Manages camera configuration with auto-detection and profiles."""
    
    # Known camera profiles with optimal settings
    CAMERA_PROFILES = {
        'logitech': {
            'brightness': 128,
            'contrast': 128,
            'saturation': 128,
            'sharpness': 128,
            'auto_exposure': True,
            'auto_focus': True,
            'auto_wb': True,
            'resolution': (1280, 720),
            'fps': 30
        },
        'microsoft': {
            'brightness': 133,
            'contrast': 5,
            'saturation': 83,
            'sharpness': 25,
            'auto_exposure': True,
            'auto_focus': True,
            'auto_wb': True,
            'resolution': (1280, 720),
            'fps': 30
        },
        'borescope': {
            'brightness': 140,
            'contrast': 150,
            'saturation': 100,
            'sharpness': 200,
            'auto_exposure': False,
            'exposure': -5,
            'auto_focus': False,
            'focus': 128,
            'auto_wb': False,
            'white_balance': 4600,
            'resolution': (1920, 1080),
            'fps': 30
        },
        'generic_webcam': {
            'brightness': 128,
            'contrast': 128,
            'saturation': 128,
            'sharpness': 128,
            'auto_exposure': True,
            'auto_focus': True,
            'auto_wb': True,
            'resolution': (1280, 720),
            'fps': 30
        }
    }
    
    # Default fallback settings
    DEFAULT_SETTINGS = {
        'brightness': 128,
        'contrast': 128,
        'saturation': 128,
        'sharpness': 128,
        'auto_exposure': True,
        'auto_focus': True,
        'auto_wb': True,
        'resolution': (1280, 720),
        'fps': 30
    }
    
    @staticmethod
    def detect_camera_type(camera_name):
        """Detect camera type from name and return appropriate profile."""
        name_lower = camera_name.lower()
        
        # Check for known manufacturers
        if 'logitech' in name_lower or 'logi' in name_lower:
            return 'logitech'
        elif 'microsoft' in name_lower or 'lifecam' in name_lower:
            return 'microsoft'
        elif 'borescope' in name_lower or 'endoscope' in name_lower or 'inspection' in name_lower:
            return 'borescope'
        elif 'usb' in name_lower and 'camera' in name_lower:
            return 'generic_webcam'
        else:
            return 'generic_webcam'
    
    @staticmethod
    def get_optimal_settings(camera_name):
        """Get optimal settings for a camera based on its type."""
        camera_type = CameraConfigManager.detect_camera_type(camera_name)
        
        if camera_type in CameraConfigManager.CAMERA_PROFILES:
            return CameraConfigManager.CAMERA_PROFILES[camera_type].copy()
        else:
            return CameraConfigManager.DEFAULT_SETTINGS.copy()
    
    @staticmethod
    def probe_camera_capabilities(cap):
        """Probe camera to determine supported properties and optimal ranges."""
        capabilities = {
            'supported_properties': {},
            'property_ranges': {},
            'recommended_settings': {}
        }
        
        properties_to_test = {
            'brightness': cv2.CAP_PROP_BRIGHTNESS,
            'contrast': cv2.CAP_PROP_CONTRAST,
            'saturation': cv2.CAP_PROP_SATURATION,
            'sharpness': cv2.CAP_PROP_SHARPNESS,
            'exposure': cv2.CAP_PROP_EXPOSURE,
            'gain': cv2.CAP_PROP_GAIN,
            'focus': cv2.CAP_PROP_FOCUS,
            'white_balance': cv2.CAP_PROP_WB_TEMPERATURE,
            'fps': cv2.CAP_PROP_FPS,
        }
        
        for name, prop in properties_to_test.items():
            try:
                # Try to read the property
                current_value = cap.get(prop)
                
                # Try to set a test value
                test_value = current_value + 1
                cap.set(prop, test_value)
                new_value = cap.get(prop)
                
                # Restore original
                cap.set(prop, current_value)
                
                # If we can read it, consider it supported
                capabilities['supported_properties'][name] = True
                capabilities['property_ranges'][name] = {
                    'current': current_value,
                    'can_set': (new_value != current_value)
                }
            except:
                capabilities['supported_properties'][name] = False
        
        # Test resolution capabilities
        test_resolutions = [
            (640, 480),
            (800, 600),
            (1280, 720),
            (1920, 1080),
            (2560, 1440),
            (3840, 2160)
        ]
        
        supported_resolutions = []
        original_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        original_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        for width, height in test_resolutions:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            if actual_width == width and actual_height == height:
                supported_resolutions.append((width, height))
        
        # Restore original resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, original_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, original_height)
        
        capabilities['supported_resolutions'] = supported_resolutions
        
        # Recommend highest supported resolution up to 1080p for performance
        if (1920, 1080) in supported_resolutions:
            capabilities['recommended_settings']['resolution'] = (1920, 1080)
        elif (1280, 720) in supported_resolutions:
            capabilities['recommended_settings']['resolution'] = (1280, 720)
        elif supported_resolutions:
            capabilities['recommended_settings']['resolution'] = supported_resolutions[-1]
        else:
            capabilities['recommended_settings']['resolution'] = (640, 480)
        
        return capabilities
    
    @staticmethod
    def apply_settings_to_camera(cap, settings):
        """Apply settings dictionary to camera."""
        results = {'applied': {}, 'failed': {}}
        
        # Apply resolution
        if 'resolution' in settings:
            width, height = settings['resolution']
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                if actual_width == width and actual_height == height:
                    results['applied']['resolution'] = (width, height)
                else:
                    results['failed']['resolution'] = f"Got {actual_width}x{actual_height}"
            except Exception as e:
                results['failed']['resolution'] = str(e)
        
        # Apply auto modes
        if 'auto_exposure' in settings:
            try:
                value = 0.75 if settings['auto_exposure'] else 0.25
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, value)
                results['applied']['auto_exposure'] = settings['auto_exposure']
            except Exception as e:
                results['failed']['auto_exposure'] = str(e)
        
        if 'auto_focus' in settings:
            try:
                value = 1 if settings['auto_focus'] else 0
                cap.set(cv2.CAP_PROP_AUTOFOCUS, value)
                results['applied']['auto_focus'] = settings['auto_focus']
            except Exception as e:
                results['failed']['auto_focus'] = str(e)
        
        if 'auto_wb' in settings:
            try:
                value = 1 if settings['auto_wb'] else 0
                cap.set(cv2.CAP_PROP_AUTO_WB, value)
                results['applied']['auto_wb'] = settings['auto_wb']
            except Exception as e:
                results['failed']['auto_wb'] = str(e)
        
        # Apply property values
        property_map = {
            'brightness': cv2.CAP_PROP_BRIGHTNESS,
            'contrast': cv2.CAP_PROP_CONTRAST,
            'saturation': cv2.CAP_PROP_SATURATION,
            'sharpness': cv2.CAP_PROP_SHARPNESS,
            'exposure': cv2.CAP_PROP_EXPOSURE,
            'gain': cv2.CAP_PROP_GAIN,
            'focus': cv2.CAP_PROP_FOCUS,
            'white_balance': cv2.CAP_PROP_WB_TEMPERATURE,
            'fps': cv2.CAP_PROP_FPS,
        }
        
        for name, prop in property_map.items():
            if name in settings:
                try:
                    cap.set(prop, settings[name])
                    actual = cap.get(prop)
                    results['applied'][name] = actual
                except Exception as e:
                    results['failed'][name] = str(e)
        
        return results
    
    @staticmethod
    def load_config(config_path='settings/camera_config.json'):
        """Load camera configuration from file."""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    @staticmethod
    def save_config(config, config_path='settings/camera_config.json'):
        """Save camera configuration to file."""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    @staticmethod
    def get_camera_settings(camera_name, config_path='settings/camera_config.json'):
        """Get settings for a specific camera, with fallback to optimal defaults."""
        config = CameraConfigManager.load_config(config_path)
        
        # Check if we have saved settings for this camera
        if 'cameras' in config and camera_name in config['cameras']:
            return config['cameras'][camera_name]
        
        # Otherwise, return optimal settings based on camera type
        return CameraConfigManager.get_optimal_settings(camera_name)
    
    @staticmethod
    def initialize_camera_with_optimal_settings(cap, camera_name, config_path='settings/camera_config.json'):
        """Initialize camera with optimal settings on first use."""
        # Get settings (saved or optimal defaults)
        settings = CameraConfigManager.get_camera_settings(camera_name, config_path)
        
        # Probe capabilities
        capabilities = CameraConfigManager.probe_camera_capabilities(cap)
        
        # Use recommended resolution if no saved preference
        if 'resolution' not in settings and 'resolution' in capabilities['recommended_settings']:
            settings['resolution'] = capabilities['recommended_settings']['resolution']
        
        # Apply settings
        results = CameraConfigManager.apply_settings_to_camera(cap, settings)
        
        return {
            'settings': settings,
            'capabilities': capabilities,
            'results': results
        }
