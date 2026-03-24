"""User preferences manager - loads/saves settings from JSON config file."""
import json
import os
import hashlib

from logger_config import get_logger

logger = get_logger(__name__)

_PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings", "user_preferences.json")

_DEFAULTS = {
    "technician_name": "",
    "default_camera_index": 0,
    "report_format": "both",          # "pdf", "docx", or "both"
    "dark_mode": False,
    "accent_color": "#77C25E",
    "default_marker_color": "#FF0000",
    "reports_output_dir": "",          # empty = default output/reports
    "captured_images_dir": "",         # empty = default output/captured_images
    "editor_password_hash": hashlib.sha256("admin".encode()).hexdigest(),
    "log_retention_days": 30,
}


class PreferencesManager:
    """Singleton manager for user preferences."""

    def __init__(self):
        self._prefs = dict(_DEFAULTS)
        self.load()

    # -- public API --

    def get(self, key: str):
        return self._prefs.get(key, _DEFAULTS.get(key))

    def set(self, key: str, value):
        self._prefs[key] = value

    def save(self):
        os.makedirs(os.path.dirname(_PREFS_PATH), exist_ok=True)
        try:
            with open(_PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._prefs, f, indent=2)
        except Exception:
            logger.warning("Failed to save preferences", exc_info=True)

    def load(self):
        if os.path.exists(_PREFS_PATH):
            try:
                with open(_PREFS_PATH, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                # Merge with defaults so new keys are always present
                for k, v in _DEFAULTS.items():
                    if k not in stored:
                        stored[k] = v
                self._prefs = stored
            except Exception:
                logger.warning("Failed to load preferences, using defaults", exc_info=True)
                self._prefs = dict(_DEFAULTS)

    def get_reports_dir(self) -> str:
        """Return the effective reports output directory."""
        custom = self._prefs.get("reports_output_dir", "")
        if custom and os.path.isdir(custom):
            return custom
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "reports")

    def get_captured_images_dir(self) -> str:
        """Return the effective captured images base directory."""
        custom = self._prefs.get("captured_images_dir", "")
        if custom and os.path.isdir(custom):
            return custom
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "captured_images")

    def check_editor_password(self, password: str) -> bool:
        return hashlib.sha256(password.encode()).hexdigest() == self._prefs.get("editor_password_hash", "")

    def set_editor_password(self, new_password: str):
        self._prefs["editor_password_hash"] = hashlib.sha256(new_password.encode()).hexdigest()

    def get_accent_colors(self) -> tuple:
        """Return (accent, hover, pressed) colors derived from accent_color."""
        base = self._prefs.get("accent_color", "#77C25E")
        # Darken for hover/pressed
        hover = self._darken(base, 0.82)
        pressed = self._darken(base, 0.65)
        return base, hover, pressed

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return f"#{r:02X}{g:02X}{b:02X}"


# Global singleton
preferences = PreferencesManager()
