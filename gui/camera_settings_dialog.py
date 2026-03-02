"""Camera settings dialog for adjusting camera properties."""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSlider, QComboBox, QGroupBox,
                             QRadioButton, QTabWidget, QWidget, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage
import cv2
import json
import os


class CameraSettingsDialog(QDialog):
    """Dialog for configuring camera settings."""
    
    # OpenCV property mappings
    PROPERTIES = {
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
    
    def __init__(self, available_cameras=None, config_path='settings/camera_config.json', parent=None):
        super().__init__(parent)
        self.available_cameras = available_cameras or []
        self.current_camera = None
        self.config_path = config_path
        self.supported_properties = {}
        self.original_settings = {}
        self.controls = {}
        
        self.setWindowTitle("Camera Settings")
        self.setMinimumSize(700, 600)
        
        self.init_ui()
        
        # Discover cameras if not provided
        if not self.available_cameras:
            self.discover_cameras()
        else:
            self.populate_camera_list()
        
        # Start preview timer
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(50)
    
    def detect_supported_properties(self):
        """Detect which properties the camera supports."""
        if not self.current_camera:
            return
            
        for name, prop in self.PROPERTIES.items():
            try:
                # Try to read the property
                value = self.current_camera.capture.get(prop)
                # Try to set it back
                self.current_camera.capture.set(prop, value)
                # Verify it was set
                new_value = self.current_camera.capture.get(prop)
                # Consider supported if we can read it (even if set doesn't work perfectly)
                self.supported_properties[name] = True
            except:
                self.supported_properties[name] = False
    
    def save_original_settings(self):
        """Save original camera settings for reset."""
        if not self.current_camera:
            return
            
        for name, prop in self.PROPERTIES.items():
            if self.supported_properties.get(name):
                try:
                    self.original_settings[name] = self.current_camera.capture.get(prop)
                except:
                    pass
        
        # Save resolution
        try:
            width = self.current_camera.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = self.current_camera.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            self.original_settings['resolution'] = (int(width), int(height))
        except:
            self.original_settings['resolution'] = (1280, 720)
    
    def discover_cameras(self):
        """Discover available cameras."""
        from camera import CameraManager
        self.available_cameras = CameraManager.discover_cameras()
        self.populate_camera_list()
    
    def populate_camera_list(self):
        """Populate the camera selector dropdown."""
        self.camera_selector.clear()
        for camera in self.available_cameras:
            self.camera_selector.addItem(camera.name)
        
        if self.available_cameras:
            self.camera_selector.setCurrentIndex(0)
    
    def on_camera_selected(self, index):
        """Handle camera selection change."""
        if index < 0 or index >= len(self.available_cameras):
            return
        
        # Close previous camera if different
        if self.current_camera and self.current_camera != self.available_cameras[index]:
            # Don't close if it's from the parent (they're still using it)
            pass
        
        self.current_camera = self.available_cameras[index]
        
        # Open camera if not already open
        if not self.current_camera.capture or not self.current_camera.capture.isOpened():
            self.current_camera.open()
        
        # Update info label
        self.info_label.setText(f"Camera: {self.current_camera.name}")
        
        # Detect supported properties
        self.supported_properties = {}
        self.detect_supported_properties()
        
        # Save original settings
        self.original_settings = {}
        self.save_original_settings()
        
        # Update UI controls
        self.update_controls_for_camera()
        
        # Load saved settings
        self.load_settings()
    
    def update_controls_for_camera(self):
        """Update control states based on camera capabilities."""
        for prop_name, control in self.controls.items():
            supported = self.supported_properties.get(prop_name, False)
            control['slider'].setEnabled(supported)
            
            # Update or add unsupported label
            if not supported:
                # Check if unsupported label already exists
                has_label = False
                for i in range(control['layout'].count()):
                    widget = control['layout'].itemAt(i).widget()
                    if widget and isinstance(widget, QLabel) and "(Not supported)" in widget.text():
                        has_label = True
                        break
                
                if not has_label:
                    unsupported = QLabel("(Not supported)")
                    unsupported.setStyleSheet("color: #999; font-style: italic;")
                    control['layout'].addWidget(unsupported)
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Camera selection at the top
        camera_select_layout = QHBoxLayout()
        camera_select_label = QLabel("Select Camera:")
        camera_select_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.camera_selector = QComboBox()
        self.camera_selector.currentIndexChanged.connect(self.on_camera_selected)
        camera_select_layout.addWidget(camera_select_label)
        camera_select_layout.addWidget(self.camera_selector, 1)
        layout.addLayout(camera_select_layout)
        
        # Camera info
        self.info_label = QLabel("Select a camera to configure")
        self.info_label.setStyleSheet("font-weight: bold; font-size: 10pt; padding: 10px; background-color: #f0f0f0; border-radius: 3px;")
        layout.addWidget(self.info_label)
        
        # Tabs for Basic/Advanced
        tabs = QTabWidget()
        tabs.addTab(self.create_basic_tab(), "Basic")
        tabs.addTab(self.create_advanced_tab(), "Advanced")
        layout.addWidget(tabs)
        
        # Preview
        preview_group = QGroupBox("Live Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setStyleSheet("border: 2px solid #ccc; background-color: #000;")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_settings)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(apply_btn)
        
        save_btn = QPushButton("Save & Close")
        save_btn.clicked.connect(self.save_and_close)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_basic_tab(self):
        """Create basic settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Resolution
        res_group = QGroupBox("Resolution")
        res_layout = QVBoxLayout()
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "640x480 (VGA)",
            "800x600 (SVGA)",
            "1280x720 (HD)",
            "1920x1080 (Full HD)",
            "2560x1440 (2K)",
            "3840x2160 (4K)"
        ])
        self.resolution_combo.setCurrentIndex(2)  # Default to HD
        self.resolution_combo.currentIndexChanged.connect(self.on_resolution_changed)
        res_layout.addWidget(self.resolution_combo)
        
        # Resolution note
        res_note = QLabel("💡 If camera output is grayscale, try resetting to defaults or use a lower resolution.")
        res_note.setStyleSheet("color: #FF9800; font-size: 9pt; padding: 5px; background-color: #FFF3E0; border-radius: 3px;")
        res_note.setWordWrap(True)
        res_layout.addWidget(res_note)
        
        res_group.setLayout(res_layout)
        layout.addWidget(res_group)
        
        # Image Quality
        quality_group = QGroupBox("Image Quality")
        quality_layout = QVBoxLayout()
        
        # Brightness
        self.controls['brightness'] = self.create_slider_control(
            "Brightness", -100, 100, 0, quality_layout, 'brightness'
        )
        
        # Contrast
        self.controls['contrast'] = self.create_slider_control(
            "Contrast", -100, 100, 0, quality_layout, 'contrast'
        )
        
        # Saturation
        self.controls['saturation'] = self.create_slider_control(
            "Saturation", -100, 100, 0, quality_layout, 'saturation'
        )
        
        # Sharpness
        self.controls['sharpness'] = self.create_slider_control(
            "Sharpness", 0, 100, 50, quality_layout, 'sharpness'
        )
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        # Exposure
        exposure_group = QGroupBox("Exposure")
        exposure_layout = QVBoxLayout()
        
        exp_mode_layout = QHBoxLayout()
        self.auto_exposure_radio = QRadioButton("Auto")
        self.manual_exposure_radio = QRadioButton("Manual")
        self.auto_exposure_radio.setChecked(True)
        self.auto_exposure_radio.toggled.connect(self.on_exposure_mode_changed)
        exp_mode_layout.addWidget(self.auto_exposure_radio)
        exp_mode_layout.addWidget(self.manual_exposure_radio)
        exp_mode_layout.addStretch()
        exposure_layout.addLayout(exp_mode_layout)
        
        self.controls['exposure'] = self.create_slider_control(
            "Exposure", -13, -1, -5, exposure_layout, 'exposure'
        )
        self.controls['exposure']['slider'].setEnabled(False)
        
        exposure_group.setLayout(exposure_layout)
        layout.addWidget(exposure_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_advanced_tab(self):
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Focus
        focus_group = QGroupBox("Focus")
        focus_layout = QVBoxLayout()
        
        focus_mode_layout = QHBoxLayout()
        self.auto_focus_radio = QRadioButton("Auto")
        self.manual_focus_radio = QRadioButton("Manual")
        self.auto_focus_radio.setChecked(True)
        self.auto_focus_radio.toggled.connect(self.on_focus_mode_changed)
        focus_mode_layout.addWidget(self.auto_focus_radio)
        focus_mode_layout.addWidget(self.manual_focus_radio)
        focus_mode_layout.addStretch()
        focus_layout.addLayout(focus_mode_layout)
        
        self.controls['focus'] = self.create_slider_control(
            "Focus", 0, 255, 128, focus_layout, 'focus'
        )
        self.controls['focus']['slider'].setEnabled(False)
        
        focus_group.setLayout(focus_layout)
        layout.addWidget(focus_group)
        
        # White Balance
        wb_group = QGroupBox("White Balance")
        wb_layout = QVBoxLayout()
        
        wb_mode_layout = QHBoxLayout()
        self.auto_wb_radio = QRadioButton("Auto")
        self.manual_wb_radio = QRadioButton("Manual")
        self.auto_wb_radio.setChecked(True)
        self.auto_wb_radio.toggled.connect(self.on_wb_mode_changed)
        wb_mode_layout.addWidget(self.auto_wb_radio)
        wb_mode_layout.addWidget(self.manual_wb_radio)
        wb_mode_layout.addStretch()
        wb_layout.addLayout(wb_mode_layout)
        
        self.controls['white_balance'] = self.create_slider_control(
            "Temperature", 2800, 6500, 4600, wb_layout, 'white_balance'
        )
        self.controls['white_balance']['slider'].setEnabled(False)
        
        wb_group.setLayout(wb_layout)
        layout.addWidget(wb_group)
        
        # Gain
        self.controls['gain'] = self.create_slider_control(
            "Gain (ISO)", 0, 100, 0, None, 'gain'
        )
        gain_group = QGroupBox("Gain")
        gain_layout = QVBoxLayout()
        gain_layout.addLayout(self.controls['gain']['layout'])
        gain_group.setLayout(gain_layout)
        layout.addWidget(gain_group)
        
        # Frame Rate
        fps_group = QGroupBox("Frame Rate")
        fps_layout = QVBoxLayout()
        
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["15 FPS", "30 FPS", "60 FPS"])
        self.fps_combo.setCurrentIndex(1)  # Default to 30 FPS
        self.fps_combo.currentIndexChanged.connect(self.on_fps_changed)
        fps_layout.addWidget(self.fps_combo)
        
        if not self.supported_properties.get('fps'):
            self.fps_combo.setEnabled(False)
            unsupported_label = QLabel("(Not supported by this camera)")
            unsupported_label.setStyleSheet("color: #999; font-style: italic;")
            fps_layout.addWidget(unsupported_label)
        
        fps_group.setLayout(fps_layout)
        layout.addWidget(fps_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_slider_control(self, label, min_val, max_val, default_val, parent_layout, prop_name):
        """Create a slider control with label and value display."""
        control_layout = QHBoxLayout()
        
        label_widget = QLabel(f"{label}:")
        label_widget.setMinimumWidth(100)
        control_layout.addWidget(label_widget)
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(lambda v: self.on_slider_changed(prop_name, v))
        control_layout.addWidget(slider)
        
        value_label = QLabel(str(default_val))
        value_label.setMinimumWidth(50)
        control_layout.addWidget(value_label)
        
        # Check if property is supported
        if not self.supported_properties.get(prop_name):
            slider.setEnabled(False)
            unsupported = QLabel("(Not supported)")
            unsupported.setStyleSheet("color: #999; font-style: italic;")
            control_layout.addWidget(unsupported)
        
        if parent_layout:
            parent_layout.addLayout(control_layout)
        
        return {
            'layout': control_layout,
            'slider': slider,
            'value_label': value_label,
            'label': label_widget
        }
    
    def on_slider_changed(self, prop_name, value):
        """Handle slider value change."""
        if prop_name in self.controls:
            self.controls[prop_name]['value_label'].setText(str(value))
    
    def on_resolution_changed(self):
        """Handle resolution change."""
        res_text = self.resolution_combo.currentText()
        res_map = {
            "640x480 (VGA)": (640, 480),
            "800x600 (SVGA)": (800, 600),
            "1280x720 (HD)": (1280, 720),
            "1920x1080 (Full HD)": (1920, 1080),
            "2560x1440 (2K)": (2560, 1440),
            "3840x2160 (4K)": (3840, 2160)
        }
        
        if res_text in res_map:
            width, height = res_map[res_text]
            try:
                self.current_camera.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.current_camera.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            except:
                pass
    
    def on_exposure_mode_changed(self):
        """Handle exposure mode change."""
        is_auto = self.auto_exposure_radio.isChecked()
        self.controls['exposure']['slider'].setEnabled(not is_auto)
        
        if self.supported_properties.get('exposure'):
            try:
                # 0.75 = auto, 0.25 = manual
                self.current_camera.capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75 if is_auto else 0.25)
            except:
                pass
    
    def on_focus_mode_changed(self):
        """Handle focus mode change."""
        is_auto = self.auto_focus_radio.isChecked()
        self.controls['focus']['slider'].setEnabled(not is_auto)
        
        if self.supported_properties.get('focus'):
            try:
                self.current_camera.capture.set(cv2.CAP_PROP_AUTOFOCUS, 1 if is_auto else 0)
            except:
                pass
    
    def on_wb_mode_changed(self):
        """Handle white balance mode change."""
        is_auto = self.auto_wb_radio.isChecked()
        self.controls['white_balance']['slider'].setEnabled(not is_auto)
        
        if self.supported_properties.get('white_balance'):
            try:
                self.current_camera.capture.set(cv2.CAP_PROP_AUTO_WB, 1 if is_auto else 0)
            except:
                pass
    
    def on_fps_changed(self):
        """Handle FPS change."""
        fps_text = self.fps_combo.currentText()
        fps_map = {"15 FPS": 15, "30 FPS": 30, "60 FPS": 60}
        
        if fps_text in fps_map and self.supported_properties.get('fps'):
            try:
                self.current_camera.capture.set(cv2.CAP_PROP_FPS, fps_map[fps_text])
            except:
                pass
    
    def apply_settings(self):
        """Apply current settings to camera."""
        try:
            # Apply all slider values
            for prop_name, control in self.controls.items():
                if self.supported_properties.get(prop_name):
                    value = control['slider'].value()
                    try:
                        self.current_camera.capture.set(self.PROPERTIES[prop_name], value)
                    except:
                        pass
            
            QMessageBox.information(self, "Settings Applied", 
                                   "Camera settings have been applied.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to apply some settings:\n{e}")
    
    def reset_to_defaults(self):
        """Reset camera to original settings."""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Reset all settings to their original values?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Restore original settings
            for name, value in self.original_settings.items():
                if name == 'resolution':
                    width, height = value
                    try:
                        self.current_camera.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        self.current_camera.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    except:
                        pass
                elif name in self.PROPERTIES:
                    try:
                        self.current_camera.capture.set(self.PROPERTIES[name], value)
                    except:
                        pass
            
            # Reset UI controls
            self.load_current_settings_to_ui()
            QMessageBox.information(self, "Reset Complete", 
                                   "Settings have been reset to defaults.")
    
    def load_current_settings_to_ui(self):
        """Load current camera settings into UI controls."""
        for prop_name, control in self.controls.items():
            if self.supported_properties.get(prop_name):
                try:
                    value = self.current_camera.capture.get(self.PROPERTIES[prop_name])
                    control['slider'].setValue(int(value))
                except:
                    pass
    
    def save_and_close(self):
        """Save settings to config file and close."""
        self.apply_settings()
        self.save_settings()
        self.accept()
    
    def save_settings(self):
        """Save current settings to config file."""
        settings = {
            'camera_name': self.current_camera.name,
            'resolution': self.resolution_combo.currentText(),
            'auto_exposure': self.auto_exposure_radio.isChecked(),
            'auto_focus': self.auto_focus_radio.isChecked(),
            'auto_wb': self.auto_wb_radio.isChecked(),
            'fps': self.fps_combo.currentText(),
            'properties': {}
        }
        
        # Save all property values
        for prop_name, control in self.controls.items():
            settings['properties'][prop_name] = control['slider'].value()
        
        # Load existing config
        config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            except:
                pass
        
        # Update config for this camera
        if 'cameras' not in config:
            config['cameras'] = {}
        
        config['cameras'][self.current_camera.name] = settings
        
        # Save config
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_settings(self):
        """Load settings from config file."""
        if not os.path.exists(self.config_path):
            return
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            if 'cameras' in config and self.current_camera.name in config['cameras']:
                settings = config['cameras'][self.current_camera.name]
                
                # Apply resolution
                if 'resolution' in settings:
                    index = self.resolution_combo.findText(settings['resolution'])
                    if index >= 0:
                        self.resolution_combo.setCurrentIndex(index)
                
                # Apply exposure mode
                if 'auto_exposure' in settings:
                    self.auto_exposure_radio.setChecked(settings['auto_exposure'])
                    self.manual_exposure_radio.setChecked(not settings['auto_exposure'])
                
                # Apply focus mode
                if 'auto_focus' in settings:
                    self.auto_focus_radio.setChecked(settings['auto_focus'])
                    self.manual_focus_radio.setChecked(not settings['auto_focus'])
                
                # Apply white balance mode
                if 'auto_wb' in settings:
                    self.auto_wb_radio.setChecked(settings['auto_wb'])
                    self.manual_wb_radio.setChecked(not settings['auto_wb'])
                
                # Apply FPS
                if 'fps' in settings:
                    index = self.fps_combo.findText(settings['fps'])
                    if index >= 0:
                        self.fps_combo.setCurrentIndex(index)
                
                # Apply property values
                if 'properties' in settings:
                    for prop_name, value in settings['properties'].items():
                        if prop_name in self.controls:
                            self.controls[prop_name]['slider'].setValue(value)
                
                # Apply to camera
                self.apply_settings()
        except Exception as e:
            print(f"Failed to load settings: {e}")
    
    def update_preview(self):
        """Update the live preview."""
        if self.current_camera:
            frame = self.current_camera.capture_frame()
            if frame is not None:
                # Convert to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Scale to fit preview
                pixmap = QPixmap.fromImage(qt_image)
                scaled = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
    
    def closeEvent(self, event):
        """Handle dialog close."""
        self.preview_timer.stop()
        super().closeEvent(event)
