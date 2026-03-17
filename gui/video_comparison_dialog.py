"""Video comparison dialog — side-by-side reference video vs live camera."""
import os
import cv2
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMessageBox, QSplitter, QSlider, QWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont
from gui.annotatable_preview import AnnotatablePreview
from gui.video_decoder import VideoDecoderThread
from gui.overlay_renderer import draw_markers_on_frame
from logger_config import get_logger

logger = get_logger(__name__)


def show_video_comparison(screen):
    """Show side-by-side comparison with reference video on left, live camera on right.
    
    Args:
        screen: WorkflowExecutionScreen instance
    """
    dialog = QDialog(screen)
    dialog.setWindowTitle("Reference Video vs Live Camera")
    dialog.setModal(False)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    # Header
    header_layout = QHBoxLayout()
    ref_label = QLabel("Reference Video")
    ref_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    ref_label.setAlignment(Qt.AlignCenter)
    header_layout.addWidget(ref_label)
    live_label = QLabel("Live Camera")
    live_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    live_label.setAlignment(Qt.AlignCenter)
    header_layout.addWidget(live_label)
    layout.addLayout(header_layout)

    splitter = QSplitter(Qt.Horizontal)

    # Left: video player
    left_container = QWidget()
    left_layout = QVBoxLayout(left_container)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(3)

    comp_video_display = QLabel()
    comp_video_display.setMinimumSize(200, 200)
    comp_video_display.setStyleSheet("border: 2px solid #FF9800; background-color: #2b2b2b;")
    comp_video_display.setAlignment(Qt.AlignCenter)
    left_layout.addWidget(comp_video_display, 1)

    # Video controls
    vc_layout = QHBoxLayout()
    play_btn = QPushButton("▶ Play")
    play_btn.setMaximumWidth(80)
    play_btn.setStyleSheet("""
        QPushButton { background-color: #FF9800; color: white; border: none;
            border-radius: 3px; font-weight: bold; padding: 4px 8px; }
        QPushButton:hover { background-color: #F57C00; }
    """)
    vc_layout.addWidget(play_btn)

    restart_btn = QPushButton("⏮ Restart")
    restart_btn.setMaximumWidth(80)
    restart_btn.setStyleSheet("""
        QPushButton { background-color: #666; color: white; border: none;
            border-radius: 3px; font-weight: bold; padding: 4px 8px; }
        QPushButton:hover { background-color: #555; }
    """)
    vc_layout.addWidget(restart_btn)

    vid_slider = QSlider(Qt.Horizontal)
    vid_slider.setMinimum(0)
    vc_layout.addWidget(vid_slider)

    time_label = QLabel("0:00 / 0:00")
    time_label.setMinimumWidth(90)
    vc_layout.addWidget(time_label)
    left_layout.addLayout(vc_layout)

    splitter.addWidget(left_container)

    # Right: live camera
    right_container = QWidget()
    right_layout = QVBoxLayout(right_container)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(5)

    live_display = AnnotatablePreview()
    live_display.setStyleSheet("border: 2px solid #2196F3; background-color: #2b2b2b;")
    live_display.setMinimumSize(400, 300)
    if hasattr(screen.preview_label, 'markers'):
        live_display.markers = [m.copy() for m in screen.preview_label.markers]

    def sync_markers():
        if hasattr(screen.preview_label, 'markers'):
            screen.preview_label.markers = [m.copy() for m in live_display.markers]
            screen.preview_label.update()
    live_display.markers_changed.connect(sync_markers)
    right_layout.addWidget(live_display, 1)
    splitter.addWidget(right_container)

    layout.addWidget(splitter, 1)

    # Action buttons
    action_layout = QHBoxLayout()

    capture_btn = QPushButton("📷 Capture Image")
    capture_btn.setMinimumHeight(35)
    capture_btn.setToolTip("Capture an image from the camera (Space)")
    capture_btn.setStyleSheet("""
        QPushButton { background-color: #77C25E; color: white; border: none;
            border-radius: 3px; padding: 8px 15px; font-weight: bold; }
        QPushButton:hover { background-color: #5FA84A; }
    """)

    def capture_from_video_comparison():
        if screen.current_camera:
            frame = screen.current_camera.capture_frame()
            if frame is not None:
                markers = live_display.markers
                if markers:
                    frame = draw_markers_on_frame(frame, markers, screen._get_marker_bgr_color())
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                camera_name = screen.current_camera.name.replace(" ", "_")
                filename = f"step{screen.current_step + 1}_{camera_name}_{timestamp}.jpg"
                filepath = os.path.join(screen.output_dir, filename)
                cv2.imwrite(filepath, frame)
                image_data = {
                    'path': filepath, 'camera': screen.current_camera.name,
                    'notes': '', 'markers': markers if markers else [],
                    'step': screen.current_step + 1
                }
                screen.captured_images.append(image_data)
                screen.step_images.append(image_data)
                live_display.clear_markers()
                if hasattr(screen.preview_label, 'markers'):
                    screen.preview_label.markers = []
                    screen.preview_label.update()
                screen.update_step_status()
                QMessageBox.information(dialog, "Image Captured",
                                        f"Image saved for step {screen.current_step + 1}")

    capture_btn.clicked.connect(capture_from_video_comparison)
    action_layout.addWidget(capture_btn)

    scan_btn = QPushButton("📱 Scan Barcode/QR")
    scan_btn.setMinimumHeight(35)
    scan_btn.setEnabled(False)
    scan_btn.setToolTip("Scan a barcode or QR code (B)")
    scan_btn.setStyleSheet("""
        QPushButton { background-color: #FF9800; color: white; border: none;
            border-radius: 3px; padding: 8px 15px; font-weight: bold; }
        QPushButton:hover { background-color: #F57C00; }
        QPushButton:disabled { background-color: #CCCCCC; color: #666666; }
    """)
    scan_btn.clicked.connect(screen.scan_barcode)
    action_layout.addWidget(scan_btn)

    record_btn = QPushButton("🔴 Start Recording")
    record_btn.setMinimumHeight(35)
    record_btn.setToolTip("Start/stop video recording (R)")
    record_btn.setStyleSheet("""
        QPushButton { background-color: #DC3545; color: white; border: none;
            border-radius: 3px; padding: 8px 15px; font-weight: bold; }
        QPushButton:hover { background-color: #C82333; }
    """)
    comp_rec = {'active': False, 'writer': None, 'path': None}

    def toggle_comp_rec():
        try:
            if not comp_rec['active']:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_path = os.path.join(screen.output_dir, f"video_{timestamp}.mp4")
                frame = screen.current_camera.capture_frame()
                if frame is None:
                    raise Exception("No frame available")
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), 30.0, (w, h))
                if not writer.isOpened():
                    raise Exception("Failed to init video writer")
                comp_rec.update({'active': True, 'writer': writer, 'path': video_path})
                record_btn.setText("⏹ Stop Recording")
                record_btn.setStyleSheet("""
                    QPushButton { background-color: #28A745; color: white; border: none;
                        border-radius: 3px; padding: 8px 15px; font-weight: bold; }
                    QPushButton:hover { background-color: #218838; }
                """)
            else:
                if comp_rec['writer']:
                    comp_rec['writer'].release()
                comp_rec['active'] = False
                record_btn.setText("🔴 Start Recording")
                record_btn.setStyleSheet("""
                    QPushButton { background-color: #DC3545; color: white; border: none;
                        border-radius: 3px; padding: 8px 15px; font-weight: bold; }
                    QPushButton:hover { background-color: #C82333; }
                """)
                if comp_rec['path'] and os.path.exists(comp_rec['path']):
                    screen.recorded_videos.append(comp_rec['path'])
                    QMessageBox.information(dialog, "Recording Stopped",
                                            f"Video saved:\n{os.path.basename(comp_rec['path'])}")
                comp_rec.update({'writer': None, 'path': None})
        except Exception as e:
            logger.error(f"Video comparison recording error: {e}")
            QMessageBox.warning(dialog, "Recording Error", str(e))
            if comp_rec['writer']:
                comp_rec['writer'].release()
            comp_rec.update({'active': False, 'writer': None, 'path': None})

    record_btn.clicked.connect(toggle_comp_rec)
    action_layout.addWidget(record_btn)
    layout.addLayout(action_layout)

    # Video player setup
    comp_slider_dragging = {'v': False}
    comp_vid_playing = {'v': False}

    def fmt_ms(ms):
        s = max(0, ms) // 1000
        return f"{s // 60}:{s % 60:02d}"

    comp_vid_thread = VideoDecoderThread(screen.ref_video_path, dialog)

    def on_comp_frame(qimg, pos_ms, duration_ms):
        pixmap = QPixmap.fromImage(qimg).scaled(
            comp_video_display.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation)
        comp_video_display.setPixmap(pixmap)
        if not comp_slider_dragging['v']:
            vid_slider.blockSignals(True)
            vid_slider.setMaximum(max(duration_ms, 1))
            vid_slider.setValue(pos_ms)
            vid_slider.blockSignals(False)
        time_label.setText(f"{fmt_ms(pos_ms)} / {fmt_ms(duration_ms)}")
        if comp_vid_playing['v'] and not comp_vid_thread._playing:
            comp_vid_playing['v'] = False
            play_btn.setText("▶ Play")

    comp_vid_thread.frame_ready.connect(on_comp_frame)
    comp_vid_thread.start()

    def toggle_play():
        if comp_vid_playing['v']:
            comp_vid_thread.pause()
            comp_vid_playing['v'] = False
            play_btn.setText("▶ Play")
        else:
            comp_vid_thread.play()
            comp_vid_playing['v'] = True
            play_btn.setText("⏸ Pause")

    def restart_vid():
        comp_vid_thread.seek(0)
        comp_vid_thread.play()
        comp_vid_playing['v'] = True
        play_btn.setText("⏸ Pause")

    def slider_pressed():
        comp_slider_dragging['v'] = True

    def slider_released():
        comp_slider_dragging['v'] = False
        comp_vid_thread.seek(vid_slider.value())

    vid_slider.sliderMoved.connect(lambda pos: comp_vid_thread.seek(pos))
    play_btn.clicked.connect(toggle_play)
    restart_btn.clicked.connect(restart_vid)
    vid_slider.sliderPressed.connect(slider_pressed)
    vid_slider.sliderReleased.connect(slider_released)

    # Live camera update timer
    def update_live():
        if screen.current_camera:
            frame = screen.current_camera.capture_frame()
            if frame is not None:
                if screen.qr_scanner:
                    barcode_type, _ = screen.qr_scanner.get_current_barcode()
                    scan_btn.setEnabled(barcode_type is not None)
                if comp_rec['active'] and comp_rec['writer']:
                    rec_frame = frame.copy()
                    if live_display.markers:
                        rec_frame = draw_markers_on_frame(rec_frame, live_display.markers, screen._get_marker_bgr_color())
                    comp_rec['writer'].write(rec_frame)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg).scaled(
                    live_display.size(), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                live_display.set_frame(pixmap)

    live_timer = QTimer()
    live_timer.timeout.connect(update_live)
    live_timer.start(33)

    # Close button
    close_btn = QPushButton("Close")
    close_btn.setMaximumHeight(30)
    close_btn.setStyleSheet("""
        QPushButton { background-color: #77C25E; color: white; border: none;
            border-radius: 3px; padding: 6px 15px; font-weight: bold; }
        QPushButton:hover { background-color: #5FA84A; }
    """)

    def close_dialog():
        comp_vid_thread.stop_thread()
        live_timer.stop()
        if comp_rec['active'] and comp_rec['writer']:
            comp_rec['writer'].release()
            if comp_rec['path'] and os.path.exists(comp_rec['path']):
                screen.recorded_videos.append(comp_rec['path'])
        dialog.close()

    close_btn.clicked.connect(close_dialog)
    dialog.destroyed.connect(lambda: (comp_vid_thread.stop_thread(), live_timer.stop()))
    layout.addWidget(close_btn)

    # Size dialog
    scr = screen.screen().geometry()
    dialog.resize(int(scr.width() * 0.8), int(scr.height() * 0.7))
    # Keyboard shortcuts
    def dialog_key_press(event):
        if event.key() == Qt.Key_Space and capture_btn.isEnabled():
            capture_from_video_comparison()
            event.accept()
        elif event.key() == Qt.Key_R and record_btn.isEnabled():
            toggle_comp_rec()
            event.accept()
        elif event.key() == Qt.Key_B and scan_btn.isEnabled():
            screen.scan_barcode()
            event.accept()
        else:
            QDialog.keyPressEvent(dialog, event)

    dialog.keyPressEvent = dialog_key_press

    dialog.show()
