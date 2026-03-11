"""USB HID barcode scanner interceptor.

Detects rapid keyboard input from USB barcode scanners (HID keyboard emulation mode).
Distinguishes scanner input from human typing by measuring inter-keystroke timing.
"""
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication


class USBBarcodeScanner(QObject):
    """Intercepts rapid keyboard input from USB HID barcode scanners."""
    barcode_scanned = pyqtSignal(str)  # Emits barcode data string

    def __init__(self, parent=None, max_key_interval_ms=50, min_length=3):
        super().__init__(parent)
        self._buffer = []
        self._min_length = min_length
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(max_key_interval_ms)
        self._timer.timeout.connect(self._reset_buffer)
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if len(self._buffer) >= self._min_length:
                    barcode = ''.join(self._buffer)
                    self._buffer.clear()
                    self._timer.stop()
                    self.barcode_scanned.emit(barcode)
                    return True  # consume the event
                self._buffer.clear()
                self._timer.stop()
                return False
            text = event.text()
            if text and text.isprintable():
                self._buffer.append(text)
                self._timer.start()  # restart timeout
        return False

    def _reset_buffer(self):
        self._buffer.clear()
