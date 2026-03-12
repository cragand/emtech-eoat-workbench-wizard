"""Background video decoder thread for reference video playback."""
import cv2
import time
import threading
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage


class VideoDecoderThread(QThread):
    """Background thread that decodes video frames and emits them at the correct rate."""
    frame_ready = pyqtSignal(QImage, int, int)  # image, position_ms, duration_ms

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self._playing = False
        self._stop = False
        self._seek_to = -1  # ms, -1 means no pending seek
        self._lock = threading.Lock()

    def play(self):
        with self._lock:
            self._playing = True

    def pause(self):
        with self._lock:
            self._playing = False

    def seek(self, ms):
        with self._lock:
            self._seek_to = ms

    def stop_thread(self):
        with self._lock:
            self._stop = True
            self._playing = False
        self.wait(2000)

    def run(self):
        cap = cv2.VideoCapture(self.path)
        if not cap.isOpened():
            return
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_ms = int(total_frames / fps * 1000)
        frame_interval = 1.0 / fps

        # Emit first frame
        ret, frame = cap.read()
        if ret:
            self._emit_frame(frame, 0, duration_ms)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        while True:
            with self._lock:
                if self._stop:
                    break
                playing = self._playing
                seek_to = self._seek_to
                self._seek_to = -1

            if seek_to >= 0:
                target_frame = int(seek_to / 1000.0 * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, min(target_frame, total_frames - 1))
                ret, frame = cap.read()
                if ret:
                    pos_ms = int(cap.get(cv2.CAP_PROP_POS_FRAMES) / fps * 1000)
                    self._emit_frame(frame, pos_ms, duration_ms)
                if not playing:
                    # Seek back so next play starts from here
                    cap.set(cv2.CAP_PROP_POS_FRAMES, max(int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1, 0))

            if not playing:
                self.msleep(30)
                continue

            t0 = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                with self._lock:
                    self._playing = False
                continue

            pos_ms = int(cap.get(cv2.CAP_PROP_POS_FRAMES) / fps * 1000)
            self._emit_frame(frame, pos_ms, duration_ms)

            # Sleep to maintain correct frame rate
            elapsed = time.perf_counter() - t0
            sleep_ms = max(0, frame_interval - elapsed)
            if sleep_ms > 0.001:
                self.msleep(int(sleep_ms * 1000))

        cap.release()

    def _emit_frame(self, frame, pos_ms, duration_ms):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self.frame_ready.emit(qimg, pos_ms, duration_ms)
