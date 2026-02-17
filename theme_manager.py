"""Theme manager for light/dark mode."""
from PyQt5.QtWidgets import QApplication


class ThemeManager:
    """Manages application theme (light/dark mode)."""
    
    # Emtech brand colors
    EMTECH_GREEN = "#77C25E"
    EMTECH_GREEN_HOVER = "#5FA84A"
    EMTECH_GREEN_PRESSED = "#4D8A3C"
    
    def __init__(self):
        self.dark_mode = False
    
    def get_stylesheet(self):
        """Get the current theme stylesheet."""
        if self.dark_mode:
            return self._get_dark_stylesheet()
        else:
            return self._get_light_stylesheet()
    
    def toggle_theme(self):
        """Toggle between light and dark mode."""
        self.dark_mode = not self.dark_mode
        return self.get_stylesheet()
    
    def _get_light_stylesheet(self):
        """Light mode stylesheet."""
        return f"""
            QWidget {{
                background-color: white !important;
                color: black !important;
            }}
            
            QLabel {{
                color: black !important;
            }}
            
            QPushButton {{
                background-color: {self.EMTECH_GREEN} !important;
                color: white !important;
                border: none;
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {self.EMTECH_GREEN_HOVER} !important;
            }}
            
            QPushButton:pressed {{
                background-color: {self.EMTECH_GREEN_PRESSED} !important;
            }}
            
            QPushButton:disabled {{
                background-color: #CCCCCC !important;
                color: #666666 !important;
            }}
            
            QLineEdit, QTextEdit {{
                background-color: white !important;
                color: black !important;
                border: 2px solid {self.EMTECH_GREEN};
                border-radius: 3px;
                padding: 8px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {self.EMTECH_GREEN_HOVER};
            }}
            
            QComboBox {{
                background-color: white !important;
                color: black !important;
                border: 2px solid {self.EMTECH_GREEN};
                border-radius: 3px;
                padding: 5px;
            }}
            
            QComboBox:hover {{
                border: 2px solid {self.EMTECH_GREEN_HOVER};
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: white !important;
                color: black !important;
                selection-background-color: {self.EMTECH_GREEN} !important;
                selection-color: white !important;
            }}
            
            QRadioButton {{
                color: black !important;
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {self.EMTECH_GREEN} !important;
                border: 2px solid {self.EMTECH_GREEN};
            }}
            
            QListWidget {{
                background-color: white !important;
                color: black !important;
                border: 2px solid {self.EMTECH_GREEN};
            }}
            
            QListWidget::item:selected {{
                background-color: {self.EMTECH_GREEN} !important;
                color: white !important;
            }}
            
            QTableWidget {{
                background-color: white !important;
                color: black !important;
                gridline-color: #CCCCCC;
            }}
            
            QHeaderView::section {{
                background-color: {self.EMTECH_GREEN} !important;
                color: white !important;
                padding: 5px;
                border: none;
            }}
        """
    
    def _get_dark_stylesheet(self):
        """Dark mode stylesheet."""
        return f"""
            QWidget {{
                background-color: #1E1E1E !important;
                color: #E0E0E0 !important;
            }}
            
            QLabel {{
                color: #E0E0E0 !important;
            }}
            
            QPushButton {{
                background-color: {self.EMTECH_GREEN} !important;
                color: white !important;
                border: none;
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {self.EMTECH_GREEN_HOVER} !important;
            }}
            
            QPushButton:pressed {{
                background-color: {self.EMTECH_GREEN_PRESSED} !important;
            }}
            
            QPushButton:disabled {{
                background-color: #3A3A3A !important;
                color: #666666 !important;
            }}
            
            QLineEdit, QTextEdit {{
                background-color: #2D2D2D !important;
                color: #E0E0E0 !important;
                border: 2px solid {self.EMTECH_GREEN};
                border-radius: 3px;
                padding: 8px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {self.EMTECH_GREEN_HOVER};
            }}
            
            QComboBox {{
                background-color: #2D2D2D !important;
                color: #E0E0E0 !important;
                border: 2px solid {self.EMTECH_GREEN};
                border-radius: 3px;
                padding: 5px;
            }}
            
            QComboBox:hover {{
                border: 2px solid {self.EMTECH_GREEN_HOVER};
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: #2D2D2D !important;
                color: #E0E0E0 !important;
                selection-background-color: {self.EMTECH_GREEN} !important;
                selection-color: white !important;
            }}
            
            QRadioButton {{
                color: #E0E0E0 !important;
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {self.EMTECH_GREEN} !important;
                border: 2px solid {self.EMTECH_GREEN};
            }}
            
            QListWidget {{
                background-color: #2D2D2D !important;
                color: #E0E0E0 !important;
                border: 2px solid {self.EMTECH_GREEN};
            }}
            
            QListWidget::item:selected {{
                background-color: {self.EMTECH_GREEN} !important;
                color: white !important;
            }}
            
            QTableWidget {{
                background-color: #2D2D2D !important;
                color: #E0E0E0 !important;
                gridline-color: #3A3A3A;
            }}
            
            QHeaderView::section {{
                background-color: {self.EMTECH_GREEN} !important;
                color: white !important;
                padding: 5px;
                border: none;
            }}
            
            QMessageBox {{
                background-color: #1E1E1E !important;
                color: #E0E0E0 !important;
            }}
            
            QMessageBox QPushButton {{
                min-width: 80px;
            }}
        """


# Global theme manager instance
theme_manager = ThemeManager()
