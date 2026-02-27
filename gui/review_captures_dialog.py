"""Dialog for reviewing and editing captured images and videos."""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
                             QMessageBox, QSplitter, QScrollArea, QWidget, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon
import cv2
import os
import subprocess
import platform


class ReviewCapturesDialog(QDialog):
    """Dialog for reviewing and editing captured images/videos."""
    
    def __init__(self, captured_images, step_images=None, current_step_requirements=None, parent=None):
        """
        Args:
            captured_images: List of all captured image dicts
            step_images: List of images for current step (for requirement validation)
            current_step_requirements: Dict with require_photo, require_annotations flags
            parent: Parent widget
        """
        super().__init__(parent)
        self.captured_images = captured_images
        self.step_images = step_images if step_images is not None else []
        self.requirements = current_step_requirements or {}
        self.current_selection = None
        
        self.setWindowTitle("Review Captured Images & Videos")
        self.setModal(True)
        self.resize(1000, 700)
        
        self.init_ui()
        self.populate_list()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QHBoxLayout()
        
        # Left side: Thumbnail list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        list_label = QLabel("Captured Items:")
        list_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(list_label)
        
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setIconSize(QSize(120, 90))
        self.thumbnail_list.setMaximumWidth(200)
        self.thumbnail_list.currentItemChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.thumbnail_list)
        
        layout.addWidget(left_widget)
        
        # Right side: Preview and editing
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px solid black; background-color: #2b2b2b;")
        self.preview_label.setMinimumSize(600, 450)
        self.preview_label.setScaledContents(False)
        right_layout.addWidget(self.preview_label)
        
        # Info and editing area
        edit_group = QGroupBox("Details")
        edit_layout = QVBoxLayout()
        
        # Camera info
        self.camera_label = QLabel("Camera: ")
        self.camera_label.setStyleSheet("font-size: 10px; color: #666;")
        edit_layout.addWidget(self.camera_label)
        
        # Step info (if applicable)
        self.step_label = QLabel("")
        self.step_label.setStyleSheet("font-size: 10px; color: #666;")
        edit_layout.addWidget(self.step_label)
        
        # Notes editing
        notes_label = QLabel("Notes:")
        notes_label.setStyleSheet("font-weight: bold;")
        edit_layout.addWidget(notes_label)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.textChanged.connect(self.on_notes_changed)
        edit_layout.addWidget(self.notes_edit)
        
        # Annotation markers editing
        self.markers_widget = QWidget()
        self.markers_layout = QFormLayout(self.markers_widget)
        self.markers_layout.setContentsMargins(0, 0, 0, 0)
        self.marker_inputs = {}
        edit_layout.addWidget(self.markers_widget)
        
        edit_group.setLayout(edit_layout)
        right_layout.addWidget(edit_group)
        
        layout.addWidget(right_widget)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.open_video_button = QPushButton("Open Video")
        self.open_video_button.setStyleSheet("""
            QPushButton {
                background-color: #77C25E;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5FA84A;
            }
        """)
        self.open_video_button.clicked.connect(self.open_video)
        self.open_video_button.setVisible(False)
        button_layout.addWidget(self.open_video_button)
        
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
        """)
        self.delete_button.clicked.connect(self.delete_selected)
        button_layout.addWidget(self.delete_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def populate_list(self):
        """Populate thumbnail list."""
        self.thumbnail_list.clear()
        
        for idx, img_data in enumerate(self.captured_images):
            img_path = img_data['path']
            media_type = img_data.get('type', 'image')
            is_video = media_type == 'video' or img_path.lower().endswith(('.avi', '.mp4', '.mov', '.mkv'))
            
            item = QListWidgetItem()
            item.setText(os.path.basename(img_path))
            item.setData(Qt.ItemDataRole.UserRole, idx)
            
            # Create thumbnail
            if is_video:
                # Use video icon for videos
                item.setText(f"🎥 {os.path.basename(img_path)}")
            else:
                # Load image thumbnail
                try:
                    pixmap = QPixmap(img_path)
                    if not pixmap.isNull():
                        icon = QIcon(pixmap)
                        item.setIcon(icon)
                except:
                    pass
            
            self.thumbnail_list.addItem(item)
        
        # Select first item
        if self.thumbnail_list.count() > 0:
            self.thumbnail_list.setCurrentRow(0)
    
    def on_selection_changed(self, current, previous):
        """Handle selection change."""
        if not current:
            return
        
        idx = current.data(Qt.ItemDataRole.UserRole)
        self.current_selection = idx
        img_data = self.captured_images[idx]
        
        # Update preview
        img_path = img_data['path']
        media_type = img_data.get('type', 'image')
        is_video = media_type == 'video' or img_path.lower().endswith(('.avi', '.mp4', '.mov', '.mkv'))
        
        if is_video:
            # Show video icon
            self.preview_label.setText(f"🎥 Video File\n\n{os.path.basename(img_path)}\n\n(Click 'Open Video' to play)")
            self.preview_label.setStyleSheet("border: 2px solid black; background-color: #2b2b2b; color: white; font-size: 14px;")
            self.open_video_button.setVisible(True)
        else:
            # Show image
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
                self.preview_label.setStyleSheet("border: 2px solid black; background-color: #2b2b2b;")
            self.open_video_button.setVisible(False)
        
        # Update info
        self.camera_label.setText(f"Camera: {img_data.get('camera', 'Unknown')}")
        
        step_info = ""
        if 'step' in img_data:
            step_info = f"Step {img_data['step']}: {img_data.get('step_title', '')}"
        self.step_label.setText(step_info)
        self.step_label.setVisible(bool(step_info))
        
        # Update notes
        self.notes_edit.blockSignals(True)
        self.notes_edit.setText(img_data.get('notes', ''))
        self.notes_edit.blockSignals(False)
        
        # Update marker annotations
        self.update_marker_inputs(img_data.get('markers', []))
    
    def update_marker_inputs(self, markers):
        """Update marker annotation input fields."""
        # Clear existing inputs
        for i in reversed(range(self.markers_layout.count())):
            self.markers_layout.itemAt(i).widget().setParent(None)
        self.marker_inputs.clear()
        
        if not markers:
            self.markers_widget.setVisible(False)
            return
        
        self.markers_widget.setVisible(True)
        
        # Add label
        label = QLabel("Annotation Markers:")
        label.setStyleSheet("font-weight: bold;")
        self.markers_layout.addRow(label)
        
        # Add input for each marker
        for marker in markers:
            label_text = marker.get('label', '')
            note = marker.get('note', '')
            
            line_edit = QLineEdit(note)
            line_edit.setPlaceholderText(f"Note for marker {label_text}")
            line_edit.textChanged.connect(lambda text, m=marker: self.on_marker_note_changed(m, text))
            
            self.markers_layout.addRow(f"{label_text}:", line_edit)
            self.marker_inputs[label_text] = line_edit
    
    def on_notes_changed(self):
        """Handle notes text change."""
        if self.current_selection is not None:
            self.captured_images[self.current_selection]['notes'] = self.notes_edit.toPlainText()
    
    def on_marker_note_changed(self, marker, text):
        """Handle marker note change."""
        marker['note'] = text
    
    def open_video(self):
        """Open video in default player."""
        if self.current_selection is None:
            return
        
        img_data = self.captured_images[self.current_selection]
        video_path = img_data['path']
        
        try:
            if platform.system() == "Windows":
                os.startfile(video_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", video_path])
            else:
                subprocess.Popen(["xdg-open", video_path])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open video:\n{str(e)}")
    
    def delete_selected(self):
        """Delete selected capture."""
        if self.current_selection is None:
            return
        
        img_data = self.captured_images[self.current_selection]
        
        # Check if this is a step image and if deletion would violate requirements
        if img_data in self.step_images:
            # Check photo requirement
            if self.requirements.get('require_photo', False):
                remaining_step_images = [img for img in self.step_images if img != img_data]
                if len(remaining_step_images) == 0:
                    QMessageBox.warning(self, "Cannot Delete",
                                       "Cannot delete - this step requires at least one photo.")
                    return
            
            # Check annotation requirement
            if self.requirements.get('require_annotations', False):
                remaining_step_images = [img for img in self.step_images if img != img_data]
                has_annotations = any(img.get('markers') and len(img.get('markers', [])) > 0 
                                     for img in remaining_step_images)
                if not has_annotations:
                    QMessageBox.warning(self, "Cannot Delete",
                                       "Cannot delete - this step requires at least one image with annotations.")
                    return
        
        # Confirm deletion
        reply = QMessageBox.question(self, "Delete Capture?",
                                    f"Delete {os.path.basename(img_data['path'])}?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Remove from lists
            self.captured_images.remove(img_data)
            if img_data in self.step_images:
                self.step_images.remove(img_data)
            
            # Delete file
            try:
                if os.path.exists(img_data['path']):
                    os.remove(img_data['path'])
            except Exception as e:
                print(f"Error deleting file: {e}")
            
            # Refresh list
            self.populate_list()
            
            if len(self.captured_images) == 0:
                QMessageBox.information(self, "All Deleted", "No more captures remaining.")
                self.accept()
