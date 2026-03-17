"""Overlay comparison dialog — side-by-side reference image vs live camera."""
import os
import cv2
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMessageBox, QCheckBox, QSlider,
                             QSplitter, QWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont
from gui.annotatable_preview import AnnotatablePreview
from gui.checkbox_widgets import CombinedReferenceImage
from gui.overlay_renderer import render_overlay_on_frame, draw_markers_on_frame
from logger_config import get_logger

logger = get_logger(__name__)


def show_overlay_comparison(screen):
    """Show side-by-side comparison of reference image and live camera.
    
    Args:
        screen: WorkflowExecutionScreen instance
    """
    if not screen.current_camera:
        return

    current_step_data = screen.workflow['steps'][screen.current_step]
    has_ref_image = bool(screen.reference_image_path and os.path.exists(screen.reference_image_path))

    if not has_ref_image:
        return

    dialog = QDialog(screen)
    dialog.setWindowTitle("Reference vs Live Camera Comparison")
    dialog.setModal(False)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    # Header
    header_layout = QHBoxLayout()
    ref_label = QLabel("Reference Image")
    ref_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    ref_label.setAlignment(Qt.AlignCenter)
    header_layout.addWidget(ref_label)

    live_label = QLabel("Live Camera")
    live_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    live_label.setAlignment(Qt.AlignCenter)
    header_layout.addWidget(live_label)

    layout.addLayout(header_layout)

    # Overlay mode controls
    overlay_controls_layout = QVBoxLayout()

    first_row = QHBoxLayout()

    overlay_checkbox = QCheckBox("Overlay Mode")
    overlay_checkbox.setStyleSheet("font-weight: bold;")
    first_row.addWidget(overlay_checkbox)

    first_row.addWidget(QLabel("Transparency:"))

    transparency_slider = QSlider(Qt.Horizontal)
    transparency_slider.setMinimum(0)
    transparency_slider.setMaximum(100)
    transparency_slider.setValue(screen.overlay_transparency)
    transparency_slider.setMaximumWidth(150)
    transparency_slider.setEnabled(False)
    first_row.addWidget(transparency_slider)

    transparency_label = QLabel(f"{screen.overlay_transparency}%")
    transparency_label.setMinimumWidth(40)
    first_row.addWidget(transparency_label)

    first_row.addStretch()
    overlay_controls_layout.addLayout(first_row)

    # Adjustment row
    adjustment_row = QHBoxLayout()

    adjustment_row.addWidget(QLabel("Scale:"))
    scale_slider = QSlider(Qt.Horizontal)
    scale_slider.setMinimum(50)
    scale_slider.setMaximum(200)
    scale_slider.setValue(screen.overlay_scale)
    scale_slider.setMaximumWidth(120)
    scale_slider.setEnabled(False)
    adjustment_row.addWidget(scale_slider)

    scale_label = QLabel("100%")
    scale_label.setMinimumWidth(45)
    adjustment_row.addWidget(scale_label)

    adjustment_row.addWidget(QLabel("X:"))
    x_offset_slider = QSlider(Qt.Horizontal)
    x_offset_slider.setMinimum(-100)
    x_offset_slider.setMaximum(100)
    x_offset_slider.setValue(screen.overlay_x_offset)
    x_offset_slider.setMaximumWidth(100)
    x_offset_slider.setEnabled(False)
    adjustment_row.addWidget(x_offset_slider)

    x_offset_label = QLabel("0px")
    x_offset_label.setMinimumWidth(40)
    adjustment_row.addWidget(x_offset_label)

    adjustment_row.addWidget(QLabel("Y:"))
    y_offset_slider = QSlider(Qt.Horizontal)
    y_offset_slider.setMinimum(-100)
    y_offset_slider.setMaximum(100)
    y_offset_slider.setValue(screen.overlay_y_offset)
    y_offset_slider.setMaximumWidth(100)
    y_offset_slider.setEnabled(False)
    adjustment_row.addWidget(y_offset_slider)

    y_offset_label = QLabel("0px")
    y_offset_label.setMinimumWidth(40)
    adjustment_row.addWidget(y_offset_label)

    adjustment_row.addWidget(QLabel("Rotation:"))
    rotation_slider = QSlider(Qt.Horizontal)
    rotation_slider.setMinimum(-180)
    rotation_slider.setMaximum(180)
    rotation_slider.setValue(screen.overlay_rotation)
    rotation_slider.setMaximumWidth(100)
    rotation_slider.setEnabled(False)
    adjustment_row.addWidget(rotation_slider)

    rotation_label = QLabel("0°")
    rotation_label.setMinimumWidth(35)
    adjustment_row.addWidget(rotation_label)

    reset_adjustments_btn = QPushButton("Reset")
    reset_adjustments_btn.setMaximumWidth(60)
    reset_adjustments_btn.setEnabled(False)
    adjustment_row.addWidget(reset_adjustments_btn)

    adjustment_row.addStretch()

    adjustment_widget = QWidget()
    adjustment_widget.setLayout(adjustment_row)
    adjustment_widget.setVisible(False)
    overlay_controls_layout.addWidget(adjustment_widget)

    layout.addLayout(overlay_controls_layout)

    # View container
    view_container = QWidget()
    view_layout = QVBoxLayout(view_container)
    view_layout.setContentsMargins(0, 0, 0, 0)

    splitter = QSplitter(Qt.Horizontal)

    # Left: Reference image with checkboxes
    ref_display = CombinedReferenceImage()
    ref_display.setStyleSheet("border: 2px solid #77C25E; background-color: #2b2b2b;")
    ref_display.setMinimumSize(400, 300)

    checkbox_data = []
    if hasattr(screen, 'workflow') and screen.workflow:
        checkbox_data = current_step_data.get('inspection_checkboxes', [])
    ref_display.set_image_and_checkboxes(screen.reference_image_path, checkbox_data)

    if hasattr(screen.reference_image, 'checkboxes'):
        for i, cb in enumerate(screen.reference_image.checkboxes):
            if i < len(ref_display.checkboxes):
                ref_display.checkboxes[i]['checked'] = cb['checked']
        ref_display.update()

    def sync_checkboxes():
        if hasattr(screen.reference_image, 'checkboxes'):
            for i, cb in enumerate(ref_display.checkboxes):
                if i < len(screen.reference_image.checkboxes):
                    screen.reference_image.checkboxes[i]['checked'] = cb['checked']
            screen.reference_image.update()
            screen.reference_image.emit_status()
            screen.update_step_status()

    ref_display.checkboxes_changed.connect(sync_checkboxes)
    splitter.addWidget(ref_display)

    # Right: Live camera
    right_container = QWidget()
    right_layout = QVBoxLayout(right_container)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(5)

    live_display = AnnotatablePreview()
    live_display.setStyleSheet("border: 2px solid #2196F3; background-color: #2b2b2b;")
    live_display.setMinimumSize(400, 300)

    if hasattr(screen.preview_label, 'markers'):
        live_display.markers = [m.copy() for m in screen.preview_label.markers]
        live_display.update()

    def sync_markers():
        if hasattr(screen.preview_label, 'markers'):
            screen.preview_label.markers = [m.copy() for m in live_display.markers]
            screen.preview_label.update()

    live_display.markers_changed.connect(sync_markers)
    right_layout.addWidget(live_display, 1)

    action_layout = QHBoxLayout()

    # Capture button
    capture_btn = QPushButton("📷 Capture Image")
    capture_btn.setMinimumHeight(35)
    capture_btn.setToolTip("Capture an image from the camera (Space)")
    capture_btn.setStyleSheet("""
        QPushButton {
            background-color: #77C25E; color: white; border: none;
            border-radius: 3px; padding: 8px 15px; font-weight: bold;
        }
        QPushButton:hover { background-color: #5FA84A; }
    """)

    # Check alpha once
    has_alpha = False
    if screen.reference_image_path and os.path.exists(screen.reference_image_path):
        ref_test = cv2.imread(screen.reference_image_path, cv2.IMREAD_UNCHANGED)
        has_alpha = ref_test is not None and len(ref_test.shape) == 3 and ref_test.shape[2] == 4

    # Overlay cache for this dialog
    _overlay_cache = {'params': None, 'canvas': None}

    def _get_overlay_params():
        return (screen.overlay_scale, screen.overlay_x_offset,
                screen.overlay_y_offset, screen.overlay_rotation,
                screen.overlay_transparency)

    def capture_from_comparison():
        if screen.current_camera:
            frame = screen.current_camera.capture_frame()
            if frame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if overlay_checkbox.isChecked() and has_alpha:
                    frame = render_overlay_on_frame(
                        frame, screen.reference_image_path, has_alpha,
                        screen.overlay_scale, screen.overlay_x_offset,
                        screen.overlay_y_offset, screen.overlay_rotation,
                        screen.overlay_transparency, _overlay_cache)
                    markers_to_use = overlay_display.markers
                else:
                    markers_to_use = live_display.markers

                if markers_to_use:
                    frame = draw_markers_on_frame(frame, markers_to_use, screen._get_marker_bgr_color())

                camera_name = screen.current_camera.name.replace(" ", "_")
                filename = f"step{screen.current_step + 1}_{camera_name}_{timestamp}.jpg"
                filepath = os.path.join(screen.output_dir, filename)
                cv2.imwrite(filepath, frame)

                image_data = {
                    'path': filepath,
                    'camera': screen.current_camera.name,
                    'notes': '',
                    'markers': markers_to_use if markers_to_use else [],
                    'step': screen.current_step + 1
                }

                screen.captured_images.append(image_data)
                screen.step_images.append(image_data)

                if overlay_checkbox.isChecked():
                    overlay_display.clear_markers()
                else:
                    live_display.clear_markers()
                    ref_display.markers = []
                    ref_display.update()

                if hasattr(screen.preview_label, 'markers'):
                    screen.preview_label.markers = []
                    screen.preview_label.update()

                screen.update_step_status()

                QMessageBox.information(dialog, "Image Captured",
                                        f"Image saved for step {screen.current_step + 1}")

    capture_btn.clicked.connect(capture_from_comparison)
    action_layout.addWidget(capture_btn)

    # Scan button
    scan_btn = QPushButton("📱 Scan Barcode/QR")
    scan_btn.setMinimumHeight(35)
    scan_btn.setEnabled(False)
    scan_btn.setToolTip("Scan a barcode or QR code (B)")
    scan_btn.setStyleSheet("""
        QPushButton {
            background-color: #FF9800; color: white; border: none;
            border-radius: 3px; padding: 8px 15px; font-weight: bold;
        }
        QPushButton:hover { background-color: #F57C00; }
        QPushButton:disabled { background-color: #CCCCCC; color: #666666; }
    """)
    scan_btn.clicked.connect(screen.scan_barcode)
    action_layout.addWidget(scan_btn)

    # Record button
    record_btn = QPushButton("🔴 Start Recording")
    record_btn.setMinimumHeight(35)
    record_btn.setToolTip("Start/stop video recording (R)")
    comparison_recording = {'active': False, 'writer': None, 'path': None, 'start_time': None}

    def toggle_comparison_recording():
        try:
            if not comparison_recording['active']:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_path = os.path.join(screen.output_dir, f"video_{timestamp}.mp4")

                frame = screen.current_camera.capture_frame()
                if frame is None:
                    raise Exception("Cannot start recording: no frame available")

                h, w = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(video_path, fourcc, 30.0, (w, h))

                if not writer.isOpened():
                    raise Exception("Failed to initialize video writer")

                comparison_recording['active'] = True
                comparison_recording['writer'] = writer
                comparison_recording['path'] = video_path
                comparison_recording['start_time'] = datetime.now()

                record_btn.setText("⏹ Stop Recording")
                record_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #28A745; color: white; border: none;
                        border-radius: 3px; padding: 8px 15px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #218838; }
                """)
                logger.info(f"Started recording in comparison view: {video_path}")
            else:
                if comparison_recording['writer']:
                    comparison_recording['writer'].release()

                comparison_recording['active'] = False
                record_btn.setText("🔴 Start Recording")
                record_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #DC3545; color: white; border: none;
                        border-radius: 3px; padding: 8px 15px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #C82333; }
                """)

                if comparison_recording['path'] and os.path.exists(comparison_recording['path']):
                    screen.recorded_videos.append(comparison_recording['path'])
                    logger.info(f"Stopped recording in comparison view: {comparison_recording['path']}")
                    QMessageBox.information(dialog, "Recording Stopped",
                                            f"Video saved:\n{os.path.basename(comparison_recording['path'])}")

                comparison_recording['writer'] = None
                comparison_recording['path'] = None
                comparison_recording['start_time'] = None

        except Exception as e:
            logger.error(f"Comparison recording error: {e}", exc_info=True)
            QMessageBox.warning(dialog, "Recording Error", f"Failed to record video:\n{str(e)}")
            comparison_recording['active'] = False
            if comparison_recording['writer']:
                comparison_recording['writer'].release()

    record_btn.clicked.connect(toggle_comparison_recording)
    action_layout.addWidget(record_btn)

    splitter.addWidget(right_container)
    view_layout.addWidget(splitter, 1)

    # Overlay display (hidden by default)
    overlay_display = AnnotatablePreview()
    overlay_display.setStyleSheet("border: 2px solid #9C27B0; background-color: #2b2b2b;")
    overlay_display.setMinimumSize(800, 600)
    overlay_display.setVisible(False)

    if hasattr(screen.preview_label, 'markers'):
        overlay_display.markers = [m.copy() for m in screen.preview_label.markers]

    def sync_overlay_markers():
        if hasattr(screen.preview_label, 'markers'):
            screen.preview_label.markers = [m.copy() for m in overlay_display.markers]
            screen.preview_label.update()

    overlay_display.markers_changed.connect(sync_overlay_markers)
    view_layout.addWidget(overlay_display, 1)

    layout.addWidget(view_container, 1)
    layout.addLayout(action_layout)

    # Toggle overlay mode
    def toggle_overlay_mode(checked):
        splitter.setVisible(not checked)
        overlay_display.setVisible(checked)
        transparency_slider.setEnabled(checked)

        if checked and has_alpha:
            adjustment_widget.setVisible(True)
            scale_slider.setEnabled(True)
            x_offset_slider.setEnabled(True)
            y_offset_slider.setEnabled(True)
            rotation_slider.setEnabled(True)
            reset_adjustments_btn.setEnabled(True)
        else:
            adjustment_widget.setVisible(False)

        if checked:
            overlay_display.markers = [m.copy() for m in live_display.markers]
            overlay_display.update()

    overlay_checkbox.toggled.connect(toggle_overlay_mode)

    if has_alpha:
        overlay_checkbox.setChecked(True)

    # Slider label updates
    def update_transparency_label(value):
        transparency_label.setText(f"{value}%")
        screen.overlay_transparency = value

    def update_scale_label(value):
        scale_label.setText(f"{value}%")
        screen.overlay_scale = value

    def update_x_offset_label(value):
        x_offset_label.setText(f"{value}px")
        screen.overlay_x_offset = value

    def update_y_offset_label(value):
        y_offset_label.setText(f"{value}px")
        screen.overlay_y_offset = value

    def update_rotation_label(value):
        rotation_label.setText(f"{value}°")
        screen.overlay_rotation = value

    def reset_adjustments():
        scale_slider.setValue(100)
        x_offset_slider.setValue(0)
        y_offset_slider.setValue(0)
        rotation_slider.setValue(0)
        screen.overlay_scale = 100
        screen.overlay_x_offset = 0
        screen.overlay_y_offset = 0
        screen.overlay_rotation = 0

    transparency_slider.valueChanged.connect(update_transparency_label)
    scale_slider.valueChanged.connect(update_scale_label)
    x_offset_slider.valueChanged.connect(update_x_offset_label)
    y_offset_slider.valueChanged.connect(update_y_offset_label)
    rotation_slider.valueChanged.connect(update_rotation_label)
    reset_adjustments_btn.clicked.connect(reset_adjustments)

    # Live update timer
    def update_comparison():
        if screen.current_camera:
            frame = screen.current_camera.capture_frame()
            if frame is not None:
                if screen.qr_scanner:
                    barcode_type, barcode_data = screen.qr_scanner.get_current_barcode()
                    scan_btn.setEnabled(barcode_type is not None)

                if comparison_recording['active'] and comparison_recording['writer']:
                    annotated_frame = frame.copy()
                    if overlay_checkbox.isChecked() and has_alpha:
                        annotated_frame = render_overlay_on_frame(
                            annotated_frame, screen.reference_image_path, has_alpha,
                            screen.overlay_scale, screen.overlay_x_offset,
                            screen.overlay_y_offset, screen.overlay_rotation,
                            screen.overlay_transparency, _overlay_cache)
                        markers_to_use = overlay_display.markers
                    else:
                        markers_to_use = live_display.markers

                    if markers_to_use:
                        annotated_frame = draw_markers_on_frame(
                            annotated_frame, markers_to_use, screen._get_marker_bgr_color())

                    comparison_recording['writer'].write(annotated_frame)

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                live_pixmap = QPixmap.fromImage(qt_image)

                if overlay_checkbox.isChecked():
                    if has_alpha and screen.reference_image_path:
                        try:
                            ref_img = cv2.imread(screen.reference_image_path, cv2.IMREAD_UNCHANGED)

                            if ref_img is not None and len(ref_img.shape) == 3 and ref_img.shape[2] == 4:
                                scale = scale_slider.value() / 100.0
                                x_offset = x_offset_slider.value()
                                y_offset = y_offset_slider.value()
                                rotation = rotation_slider.value()

                                new_w = int(ref_img.shape[1] * scale)
                                new_h = int(ref_img.shape[0] * scale)

                                if new_w > 0 and new_h > 0:
                                    ref_scaled = cv2.resize(ref_img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

                                    if rotation != 0:
                                        center = (new_w // 2, new_h // 2)
                                        rot_matrix = cv2.getRotationMatrix2D(center, rotation, 1.0)
                                        ref_scaled = cv2.warpAffine(ref_scaled, rot_matrix, (new_w, new_h),
                                                                     borderMode=cv2.BORDER_CONSTANT,
                                                                     borderValue=(0, 0, 0, 0))

                                    canvas = np.zeros((h, w, 4), dtype=np.uint8)
                                    x_pos = (w - new_w) // 2 + x_offset
                                    y_pos = (h - new_h) // 2 + y_offset

                                    x_start = max(0, x_pos)
                                    y_start = max(0, y_pos)
                                    x_end = min(w, x_pos + new_w)
                                    y_end = min(h, y_pos + new_h)

                                    src_x_start = max(0, -x_pos)
                                    src_y_start = max(0, -y_pos)
                                    src_x_end = src_x_start + (x_end - x_start)
                                    src_y_end = src_y_start + (y_end - y_start)

                                    if x_end > x_start and y_end > y_start:
                                        canvas[y_start:y_end, x_start:x_end] = ref_scaled[src_y_start:src_y_end, src_x_start:src_x_end]

                                    overlay_bgr = canvas[:, :, :3]
                                    overlay_alpha = canvas[:, :, 3].astype(float) / 255.0
                                else:
                                    ref_resized = cv2.resize(ref_img, (w, h))
                                    overlay_bgr = ref_resized[:, :, :3]
                                    overlay_alpha = ref_resized[:, :, 3].astype(float) / 255.0

                                overlay_alpha = overlay_alpha * (transparency_slider.value() / 100.0)
                                alpha_3ch = np.stack([overlay_alpha] * 3, axis=2)

                                blended = (overlay_bgr.astype(float) * alpha_3ch +
                                           frame.astype(float) * (1 - alpha_3ch)).astype(np.uint8)

                                rgb_blended = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
                                rgb_blended = np.ascontiguousarray(rgb_blended)
                                qt_blended = QImage(rgb_blended.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                                overlay_pixmap = QPixmap.fromImage(qt_blended)
                                overlay_display.set_frame(overlay_pixmap)
                            else:
                                ref_img_bgr = cv2.imread(screen.reference_image_path)
                                if ref_img_bgr is not None:
                                    ref_resized = cv2.resize(ref_img_bgr, (w, h))
                                    alpha_val = transparency_slider.value() / 100.0
                                    blended = cv2.addWeighted(ref_resized, alpha_val, frame, 1 - alpha_val, 0)
                                    rgb_blended = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
                                    qt_blended = QImage(rgb_blended.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                                    overlay_pixmap = QPixmap.fromImage(qt_blended)
                                    overlay_display.set_frame(overlay_pixmap)
                        except Exception as e:
                            logger.error(f"Error in transparent overlay: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        if screen.reference_image_path:
                            ref_img = cv2.imread(screen.reference_image_path)
                            if ref_img is not None:
                                ref_resized = cv2.resize(ref_img, (w, h))
                                alpha = transparency_slider.value() / 100.0
                                blended = cv2.addWeighted(ref_resized, alpha, frame, 1 - alpha, 0)
                                rgb_blended = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
                                qt_blended = QImage(rgb_blended.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                                overlay_pixmap = QPixmap.fromImage(qt_blended)
                                overlay_display.set_frame(overlay_pixmap)
                else:
                    live_display.set_frame(live_pixmap)

    comparison_timer = QTimer()
    comparison_timer.timeout.connect(update_comparison)
    comparison_timer.start(100)

    # Close button
    close_button = QPushButton("Close")
    close_button.setMaximumHeight(30)
    close_button.setFocusPolicy(Qt.NoFocus)
    close_button.setStyleSheet("""
        QPushButton {
            background-color: #77C25E; color: white; border: none;
            border-radius: 3px; padding: 6px 15px; font-weight: bold;
        }
        QPushButton:hover { background-color: #5FA84A; }
    """)

    def close_dialog():
        if comparison_recording['active'] and comparison_recording['writer']:
            comparison_recording['writer'].release()
            if comparison_recording['path'] and os.path.exists(comparison_recording['path']):
                screen.recorded_videos.append(comparison_recording['path'])
                logger.info(f"Auto-saved recording on dialog close: {comparison_recording['path']}")
        comparison_timer.stop()
        dialog.close()

    close_button.clicked.connect(close_dialog)

    def cleanup_comparison():
        comparison_timer.stop()
        if comparison_recording['active'] and comparison_recording['writer']:
            comparison_recording['writer'].release()

    dialog.destroyed.connect(cleanup_comparison)

    layout.addWidget(close_button)

    # Size dialog based on reference image
    ref_pixmap = QPixmap(screen.reference_image_path)
    if not ref_pixmap.isNull():
        img_width = ref_pixmap.width()
        img_height = ref_pixmap.height()
        scr = screen.screen().geometry()
        max_width = int(scr.width() * 0.9)
        max_height = int(scr.height() * 0.8)
        panel_width = min(img_width, max_width // 2 - 50)
        panel_height = min(img_height, max_height - 100)
        dialog.resize(panel_width * 2 + 100, panel_height + 100)
    else:
        scr = screen.screen().geometry()
        dialog.resize(int(scr.width() * 0.7), int(scr.height() * 0.6))

    # Keyboard shortcuts
    def dialog_key_press(event):
        if event.key() == Qt.Key_Space and capture_btn.isEnabled():
            capture_from_comparison()
            event.accept()
        elif event.key() == Qt.Key_R and record_btn.isEnabled():
            toggle_comparison_recording()
            event.accept()
        elif event.key() == Qt.Key_B and scan_btn.isEnabled():
            screen.scan_barcode()
            event.accept()
        else:
            QDialog.keyPressEvent(dialog, event)

    dialog.keyPressEvent = dialog_key_press

    dialog.show()
