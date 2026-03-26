"""Workflow report generation and display."""
import os
import platform
import subprocess
import cv2
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMessageBox, QRadioButton, QButtonGroup)
from reports import generate_reports
from preferences_manager import preferences
from logger_config import get_logger

logger = get_logger(__name__)


def generate_checkbox_image(ref_image_path, checkboxes, step_index, output_dir, serial_number):
    """Generate an image showing the reference with checkbox completion status.
    
    Returns:
        Path to generated checkbox image, or None on failure.
    """
    if not os.path.exists(ref_image_path):
        return None

    try:
        img = cv2.imread(ref_image_path)
        if img is None:
            return None

        h, w = img.shape[:2]

        for cb in checkboxes:
            x = int(cb['x'] * w)
            y = int(cb['y'] * h)
            is_checked = cb.get('checked', False)

            color = (7, 193, 255)  # BGR of #FFC107 (amber)
            fill_alpha = 0.7 if is_checked else 0.4

            cv2.rectangle(img, (x - 16, y - 16), (x + 16, y + 16), color, 3)

            overlay = img.copy()
            cv2.rectangle(overlay, (x - 16, y - 16), (x + 16, y + 16), color, -1)
            cv2.addWeighted(overlay, fill_alpha, img, 1 - fill_alpha, 0, img)

            if is_checked:
                cv2.line(img, (x - 8, y), (x - 3, y + 8), (0, 0, 0), 3)
                cv2.line(img, (x - 3, y + 8), (x + 10, y - 8), (0, 0, 0), 3)

        serial_prefix = serial_number if serial_number else "unknown"
        filename = f"{serial_prefix}_step{step_index + 1}_checkboxes.jpg"
        output_path = os.path.join(output_dir, filename)
        cv2.imwrite(output_path, img)

        return output_path

    except Exception as e:
        logger.error(f"Error generating checkbox image: {e}")
        return None


def generate_workflow_report(screen):
    """Generate PDF and DOCX reports for completed workflow.
    
    Args:
        screen: WorkflowExecutionScreen instance (needs workflow, step_results,
                step_checkbox_states, captured_images, recorded_videos,
                serial_number, technician, description, output_dir, reference_image)
    Returns:
        Tuple of (pdf_path, docx_path)
    """
    # Store final step's checkbox state
    step = screen.workflow['steps'][screen.current_step]
    if step.get('inspection_checkboxes'):
        screen.step_checkbox_states[screen.current_step] = [
            {'x': cb['x'], 'y': cb['y'], 'checked': cb['checked']}
            for cb in screen.reference_image.checkboxes
        ]

    workflow_name = screen.workflow.get('name', 'Workflow')

    checklist_data = []
    for i, step in enumerate(screen.workflow['steps']):
        step_title = step.get('title', f'Step {i + 1}')
        step_description = step.get('instructions', '')
        has_pass_fail = step.get('require_pass_fail', False) or bool(step.get('inspection_checkboxes'))

        if i in screen.step_results:
            passed = screen.step_results[i]
        else:
            passed = True
            if i in screen.step_checkbox_states:
                checkbox_states = screen.step_checkbox_states[i]
                if isinstance(checkbox_states, list):
                    checked_count = sum(1 for cb in checkbox_states if cb.get('checked', False))
                    if checked_count < len(checkbox_states):
                        passed = False

        checkbox_image = None
        if step.get('reference_image') and os.path.exists(step.get('reference_image', '')):
            if i in screen.step_checkbox_states:
                checkbox_states = screen.step_checkbox_states[i]
            else:
                checkbox_states = [{'x': cb['x'], 'y': cb['y'], 'checked': False}
                                   for cb in step.get('inspection_checkboxes', [])]

            if checkbox_states:
                checkbox_image = generate_checkbox_image(
                    step.get('reference_image'),
                    checkbox_states,
                    i,
                    screen.output_dir,
                    screen.serial_number
                )

        checklist_data.append({
            'name': step_title,
            'description': step_description,
            'passed': passed,
            'has_pass_fail': has_pass_fail,
            'checkbox_image': checkbox_image,
            'step_number': i + 1
        })

    all_barcode_scans = []
    for img in screen.captured_images:
        if 'barcode_scans' in img:
            all_barcode_scans.extend(img['barcode_scans'])

    pdf_path, docx_path = generate_reports(
        serial_number=screen.serial_number,
        technician=screen.technician,
        description=screen.description,
        images=screen.captured_images,
        mode_name=workflow_name,
        workflow_name=workflow_name,
        checklist_data=checklist_data,
        video_paths=screen.recorded_videos,
        barcode_scans=all_barcode_scans if all_barcode_scans else None,
        output_dir=preferences.get_reports_dir()
    )

    return pdf_path, docx_path


def show_report_dialog(parent, pdf_path, docx_path, image_count):
    """Show enhanced report dialog with view options."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Reports Generated")
    dialog.setModal(True)
    dialog.setMinimumWidth(500)

    layout = QVBoxLayout()

    success_label = QLabel("✓ PDF and DOCX reports generated successfully!")
    success_label.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
    layout.addWidget(success_label)

    # Warn if reports were saved to fallback location
    if preferences.is_reports_dir_fallback():
        fallback_label = QLabel(
            f"⚠️ Custom reports folder is unavailable. "
            f"Reports saved locally instead."
        )
        fallback_label.setWordWrap(True)
        fallback_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #E65100; padding: 4px;")
        layout.addWidget(fallback_label)

    layout.addSpacing(10)

    info_label = QLabel(
        f"PDF: {pdf_path}\n\n"
        f"DOCX: {docx_path}\n\n"
        f"Images included: {image_count}"
    )
    info_label.setWordWrap(True)
    info_label.setStyleSheet("font-size: 11px;")
    layout.addWidget(info_label)

    layout.addSpacing(15)

    format_label = QLabel("Select format to view:")
    format_label.setStyleSheet("font-weight: bold;")
    layout.addWidget(format_label)

    format_group = QButtonGroup(dialog)
    pdf_radio = QRadioButton("PDF")
    pdf_radio.setChecked(True)
    docx_radio = QRadioButton("DOCX")

    format_group.addButton(pdf_radio, 1)
    format_group.addButton(docx_radio, 2)

    format_layout = QHBoxLayout()
    format_layout.addWidget(pdf_radio)
    format_layout.addWidget(docx_radio)
    format_layout.addStretch()
    layout.addLayout(format_layout)

    layout.addSpacing(15)

    button_layout = QHBoxLayout()

    view_button = QPushButton("View Report")
    view_button.setStyleSheet("""
        QPushButton {
            background-color: #77C25E; color: white; border: none;
            border-radius: 3px; padding: 8px 15px; font-weight: bold;
        }
        QPushButton:hover { background-color: #5FA84A; }
    """)

    def open_report():
        file_path = pdf_path if pdf_radio.isChecked() else docx_path
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
            dialog.accept()
        except Exception as e:
            QMessageBox.warning(dialog, "Error", f"Could not open file:\n{str(e)}")

    view_button.clicked.connect(open_report)
    button_layout.addWidget(view_button)

    menu_button = QPushButton("Return to Menu")
    menu_button.setStyleSheet("""
        QPushButton {
            background-color: #333333; color: white; border: none;
            border-radius: 3px; padding: 8px 15px; font-weight: bold;
        }
        QPushButton:hover { background-color: #555555; }
    """)
    menu_button.clicked.connect(dialog.accept)
    button_layout.addWidget(menu_button)

    layout.addLayout(button_layout)
    dialog.setLayout(layout)
    dialog.exec_()
