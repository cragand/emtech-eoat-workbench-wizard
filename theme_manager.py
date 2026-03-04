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
                background-color: white;
                color: black;
            }}
            
            QLabel {{
                color: black;
            }}
            
            QPushButton {{
                background-color: {self.EMTECH_GREEN};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {self.EMTECH_GREEN_HOVER};
            }}
            
            QPushButton:pressed {{
                background-color: {self.EMTECH_GREEN_PRESSED};
            }}
            
            QPushButton:disabled {{
                background-color: #CCCCCC;
                color: #666666;
            }}
            
            QLineEdit, QTextEdit {{
                background-color: white;
                color: black;
                border: 2px solid {self.EMTECH_GREEN};
                border-radius: 3px;
                padding: 8px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {self.EMTECH_GREEN_HOVER};
            }}
            
            QComboBox {{
                background-color: white;
                color: black;
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
                background-color: white;
                color: black;
                selection-background-color: {self.EMTECH_GREEN};
                selection-color: white;
            }}
            
            QRadioButton {{
                color: black;
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {self.EMTECH_GREEN};
                border: 2px solid {self.EMTECH_GREEN};
            }}
            
            QListWidget {{
                background-color: white;
                color: black;
                border: 2px solid {self.EMTECH_GREEN};
            }}
            
            QListWidget::item {{
                color: black;
            }}
            
            QListWidget::item:selected {{
                background-color: {self.EMTECH_GREEN};
                color: white;
            }}
            
            QTableWidget {{
                background-color: white;
                color: black;
                gridline-color: #CCCCCC;
            }}
            
            QHeaderView::section {{
                background-color: {self.EMTECH_GREEN};
                color: white;
                padding: 5px;
                border: none;
            }}
            
            QDialog {{
                background-color: white;
                color: black;
            }}
            
            QTabWidget::pane {{
                border: 2px solid {self.EMTECH_GREEN};
                background-color: white;
            }}
            
            QTabBar::tab {{
                background-color: #E0E0E0;
                color: black;
                padding: 8px 16px;
                border: 1px solid #CCCCCC;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }}
            
            QTabBar::tab:selected {{
                background-color: white;
                color: black;
                font-weight: bold;
            }}
            
            QTabBar::tab:hover {{
                background-color: #F0F0F0;
            }}
            
            QGroupBox {{
                border: 2px solid {self.EMTECH_GREEN};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: black;
            }}
        """
    
    def _get_dark_stylesheet(self):
        """Dark mode stylesheet."""
        return f"""
            QWidget {{
                background-color: #1E1E1E;
                color: #E0E0E0;
            }}
            
            QLabel {{
                color: #E0E0E0;
            }}
            
            QPushButton {{
                background-color: {self.EMTECH_GREEN};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {self.EMTECH_GREEN_HOVER};
            }}
            
            QPushButton:pressed {{
                background-color: {self.EMTECH_GREEN_PRESSED};
            }}
            
            QPushButton:disabled {{
                background-color: #3A3A3A;
                color: #888888;
            }}
            
            QLineEdit, QTextEdit {{
                background-color: #2D2D2D;
                color: #E0E0E0;
                border: 2px solid {self.EMTECH_GREEN};
                border-radius: 3px;
                padding: 8px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {self.EMTECH_GREEN_HOVER};
            }}
            
            QComboBox {{
                background-color: #2D2D2D;
                color: #E0E0E0;
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
                background-color: #2D2D2D;
                color: #E0E0E0;
                selection-background-color: {self.EMTECH_GREEN};
                selection-color: white;
            }}
            
            QRadioButton {{
                color: #E0E0E0;
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {self.EMTECH_GREEN};
                border: 2px solid {self.EMTECH_GREEN};
            }}
            
            QListWidget {{
                background-color: #2D2D2D;
                color: #E0E0E0;
                border: 2px solid {self.EMTECH_GREEN};
            }}
            
            QListWidget::item {{
                color: #E0E0E0;
            }}
            
            QListWidget::item:selected {{
                background-color: {self.EMTECH_GREEN};
                color: white;
            }}
            
            QTableWidget {{
                background-color: #2D2D2D;
                color: #E0E0E0;
                gridline-color: #3A3A3A;
            }}
            
            QTableWidget::item {{
                color: #E0E0E0;
            }}
            
            QHeaderView::section {{
                background-color: {self.EMTECH_GREEN};
                color: white;
                padding: 5px;
                border: none;
            }}
            
            QDialog {{
                background-color: #1E1E1E;
                color: #E0E0E0;
            }}
            
            QMessageBox {{
                background-color: #1E1E1E;
                color: #E0E0E0;
            }}
            
            QMessageBox QLabel {{
                color: #E0E0E0;
            }}
            
            QMessageBox QPushButton {{
                min-width: 80px;
            }}
            
            QTabWidget::pane {{
                border: 2px solid {self.EMTECH_GREEN};
                background-color: #1E1E1E;
            }}
            
            QTabBar::tab {{
                background-color: #2D2D2D;
                color: #E0E0E0;
                padding: 8px 16px;
                border: 1px solid #3A3A3A;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }}
            
            QTabBar::tab:selected {{
                background-color: #1E1E1E;
                color: #E0E0E0;
                font-weight: bold;
            }}
            
            QTabBar::tab:hover {{
                background-color: #3A3A3A;
            }}
            
            QGroupBox {{
                border: 2px solid {self.EMTECH_GREEN};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #E0E0E0;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #E0E0E0;
            }}
        """


# Global theme manager instance
theme_manager = ThemeManager()
