"""User preferences dialog."""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QComboBox, QTabWidget, QWidget, QFileDialog,
                             QSpinBox, QMessageBox, QGroupBox, QFormLayout, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from preferences_manager import preferences
from logger_config import get_logger

logger = get_logger(__name__)


class ColorPickerButton(QPushButton):
    """Button that shows a color and opens a color dialog on click."""

    def __init__(self, initial_color="#77C25E", parent=None):
        super().__init__(parent)
        self._color = initial_color
        self.setFixedSize(60, 30)
        self._update_style()
        self.clicked.connect(self._pick)

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 2px solid #888;
                border-radius: 3px;
            }}
            QPushButton:hover {{ border-color: #333; }}
        """)

    def _pick(self):
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self._color), self, "Choose Color")
        if color.isValid():
            self._color = color.name()
            self._update_style()

    def color(self):
        return self._color

    def set_color(self, c):
        self._color = c
        self._update_style()


class PreferencesDialog(QDialog):
    """Tabbed preferences dialog."""

    # Signal-free: caller checks result() and reads preferences singleton after accept.

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Preferences")
        self.setMinimumSize(520, 420)
        self._build_ui()
        self._load_current()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "General")
        self.tabs.addTab(self._build_appearance_tab(), "Appearance")
        self.tabs.addTab(self._build_paths_tab(), "Paths")
        self.tabs.addTab(self._build_security_tab(), "Security")
        layout.addWidget(self.tabs)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #888; color: white; border: none; border-radius: 3px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #666; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    # -- tab builders --

    def _build_general_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)

        self.tech_input = QLineEdit()
        self.tech_input.setPlaceholderText("Remembered between sessions")
        form.addRow("Technician Name:", self.tech_input)

        self.camera_spin = QSpinBox()
        self.camera_spin.setRange(0, 10)
        self.camera_spin.setToolTip("Camera index to select by default")
        form.addRow("Default Camera Index:", self.camera_spin)

        self.report_combo = QComboBox()
        self.report_combo.addItems(["Both PDF & DOCX", "PDF Only", "DOCX Only"])
        form.addRow("Report Format:", self.report_combo)

        self.log_days_spin = QSpinBox()
        self.log_days_spin.setRange(1, 365)
        self.log_days_spin.setSuffix(" days")
        form.addRow("Log Retention:", self.log_days_spin)

        return w

    def _build_appearance_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)

        self.dark_mode_check = QCheckBox("Enable Dark Mode")
        form.addRow("Theme:", self.dark_mode_check)

        accent_layout = QHBoxLayout()
        self.accent_btn = ColorPickerButton()
        reset_accent = QPushButton("Reset to Default")
        reset_accent.setMaximumWidth(130)
        reset_accent.clicked.connect(lambda: self.accent_btn.set_color("#77C25E"))
        accent_layout.addWidget(self.accent_btn)
        accent_layout.addWidget(reset_accent)
        accent_layout.addStretch()
        form.addRow("Accent Color:", accent_layout)

        marker_layout = QHBoxLayout()
        self.marker_btn = ColorPickerButton("#FF0000")
        reset_marker = QPushButton("Reset to Default")
        reset_marker.setMaximumWidth(130)
        reset_marker.clicked.connect(lambda: self.marker_btn.set_color("#FF0000"))
        marker_layout.addWidget(self.marker_btn)
        marker_layout.addWidget(reset_marker)
        marker_layout.addStretch()
        form.addRow("Default Marker Color:", marker_layout)

        return w

    def _build_paths_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)

        note = QLabel("Leave blank to use the default application directories.")
        note.setStyleSheet("color: #888; font-size: 10px;")
        form.addRow(note)

        self.reports_dir_input = QLineEdit()
        self.reports_dir_input.setPlaceholderText("Default: output/reports")
        reports_browse = QPushButton("Browse…")
        reports_browse.setMaximumWidth(80)
        reports_browse.clicked.connect(lambda: self._browse_dir(self.reports_dir_input))
        rl = QHBoxLayout()
        rl.addWidget(self.reports_dir_input)
        rl.addWidget(reports_browse)
        form.addRow("Reports Folder:", rl)

        self.images_dir_input = QLineEdit()
        self.images_dir_input.setPlaceholderText("Default: output/captured_images")
        images_browse = QPushButton("Browse…")
        images_browse.setMaximumWidth(80)
        images_browse.clicked.connect(lambda: self._browse_dir(self.images_dir_input))
        il = QHBoxLayout()
        il.addWidget(self.images_dir_input)
        il.addWidget(images_browse)
        form.addRow("Captured Images Folder:", il)

        return w

    def _build_security_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)

        note = QLabel("Change the password used to access the Workflow Editor.")
        note.setStyleSheet("color: #888; font-size: 10px;")
        form.addRow(note)

        self.current_pw = QLineEdit()
        self.current_pw.setEchoMode(QLineEdit.Password)
        form.addRow("Current Password:", self.current_pw)

        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.Password)
        form.addRow("New Password:", self.new_pw)

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.Password)
        form.addRow("Confirm New Password:", self.confirm_pw)

        return w

    # -- helpers --

    def _browse_dir(self, line_edit):
        d = QFileDialog.getExistingDirectory(self, "Select Folder", line_edit.text())
        if d:
            line_edit.setText(d)

    def _load_current(self):
        self.tech_input.setText(preferences.get("technician_name") or "")
        self.camera_spin.setValue(preferences.get("default_camera_index") or 0)

        fmt = preferences.get("report_format") or "both"
        self.report_combo.setCurrentIndex({"both": 0, "pdf": 1, "docx": 2}.get(fmt, 0))

        self.log_days_spin.setValue(preferences.get("log_retention_days") or 30)

        self.dark_mode_check.setChecked(preferences.get("dark_mode") or False)
        self.accent_btn.set_color(preferences.get("accent_color") or "#77C25E")
        self.marker_btn.set_color(preferences.get("default_marker_color") or "#FF0000")

        self.reports_dir_input.setText(preferences.get("reports_output_dir") or "")
        self.images_dir_input.setText(preferences.get("captured_images_dir") or "")

    def _on_save(self):
        # Handle password change first (optional)
        if self.new_pw.text():
            if not preferences.check_editor_password(self.current_pw.text()):
                QMessageBox.warning(self, "Password Error", "Current password is incorrect.")
                self.tabs.setCurrentIndex(3)
                return
            if self.new_pw.text() != self.confirm_pw.text():
                QMessageBox.warning(self, "Password Error", "New passwords do not match.")
                self.tabs.setCurrentIndex(3)
                return
            if len(self.new_pw.text()) < 3:
                QMessageBox.warning(self, "Password Error", "Password must be at least 3 characters.")
                self.tabs.setCurrentIndex(3)
                return
            preferences.set_editor_password(self.new_pw.text())

        # Validate custom paths
        for label, line_edit in [("Reports Folder", self.reports_dir_input),
                                  ("Captured Images Folder", self.images_dir_input)]:
            path = line_edit.text().strip()
            if path and not os.path.isdir(path):
                QMessageBox.warning(self, "Invalid Path",
                                    f"{label} does not exist:\n{path}")
                self.tabs.setCurrentIndex(2)
                return

        preferences.set("technician_name", self.tech_input.text().strip())
        preferences.set("default_camera_index", self.camera_spin.value())
        preferences.set("report_format", ["both", "pdf", "docx"][self.report_combo.currentIndex()])
        preferences.set("log_retention_days", self.log_days_spin.value())
        preferences.set("dark_mode", self.dark_mode_check.isChecked())
        preferences.set("accent_color", self.accent_btn.color())
        preferences.set("default_marker_color", self.marker_btn.color())
        preferences.set("reports_output_dir", self.reports_dir_input.text().strip())
        preferences.set("captured_images_dir", self.images_dir_input.text().strip())

        preferences.save()
        self.accept()
