"""DOCX report generator for QC and maintenance workflows."""
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import datetime
import os


class DOCXReportGenerator:
    """Generate DOCX reports for QC and maintenance sessions."""
    
    def __init__(self, output_dir="output/reports"):
        """Initialize DOCX generator.
        
        Args:
            output_dir: Directory to save generated reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(self, serial_number, description, images, mode_name="General Capture", 
                       workflow_name=None, checklist_data=None):
        """Generate a DOCX report.
        
        Args:
            serial_number: Serial number or identifier
            description: Job description
            images: List of image file paths OR list of dicts with {path, camera, notes}
            mode_name: Name of the mode used
            workflow_name: Optional workflow name (for Mode 2/3)
            checklist_data: Optional list of checklist items with status
            
        Returns:
            Path to generated DOCX file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        serial = serial_number if serial_number else "unknown"
        filename = f"{serial}_{timestamp}.docx"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = Document()
        
        # Set default font
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(11)
        
        # Title - determine report type based on mode_name
        if "Mode 1" in mode_name or "General" in mode_name or "Capture" in mode_name:
            report_title = "Emtech EOAT Report - Inspection"
        elif "Mode 2" in mode_name or "QC" in mode_name:
            report_title = "Emtech EOAT Report - QC"
        elif "Mode 3" in mode_name or "Maintenance" in mode_name:
            report_title = "Emtech EOAT Report - Maintenance/Repair"
        else:
            report_title = "Emtech EOAT Report - Inspection"
        
        title = doc.add_heading(report_title, level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title.runs[0]
        title_run.font.color.rgb = RGBColor(119, 194, 94)  # Emtech green #77C25E
        
        # Session Information
        doc.add_heading('Session Information', level=2)
        
        # Info table
        table = doc.add_table(rows=4, cols=2)
        table.style = 'Light Grid Accent 1'
        
        # Serial Number
        table.rows[0].cells[0].text = 'Serial Number:'
        table.rows[0].cells[1].text = serial_number if serial_number else "N/A"
        
        # Mode
        table.rows[1].cells[0].text = 'Mode:'
        table.rows[1].cells[1].text = mode_name
        
        # Date/Time
        table.rows[2].cells[0].text = 'Date/Time:'
        table.rows[2].cells[1].text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Workflow (if applicable)
        if workflow_name:
            table.rows[3].cells[0].text = 'Workflow:'
            table.rows[3].cells[1].text = workflow_name
        else:
            # Remove the extra row if no workflow
            table._element.remove(table.rows[3]._element)
        
        # Make first column bold
        for row in table.rows:
            row.cells[0].paragraphs[0].runs[0].font.bold = True
        
        doc.add_paragraph()
        
        # Description as separate section
        if description:
            doc.add_heading('Description', level=3)
            doc.add_paragraph(description)
            doc.add_paragraph()
        
        # Checklist (if provided)
        if checklist_data:
            doc.add_heading('Checklist Results', level=2)
            
            for item in checklist_data:
                # Step name
                p = doc.add_paragraph()
                p.add_run(item['name']).bold = True
                
                # Status
                status = "✓ Pass" if item.get('passed', False) else "✗ Fail"
                status_run = p.add_run(f" - {status}")
                status_run.bold = True
                if item.get('passed', False):
                    status_run.font.color.rgb = RGBColor(76, 175, 80)  # Green
                else:
                    status_run.font.color.rgb = RGBColor(244, 67, 54)  # Red
                
                # Description
                if item.get('description'):
                    desc_text = item['description'][:200] + "..." if len(item['description']) > 200 else item['description']
                    p = doc.add_paragraph()
                    p.add_run(desc_text).italic = True
                
                # Checkbox image
                if item.get('checkbox_image') and os.path.exists(item['checkbox_image']):
                    try:
                        doc.add_picture(item['checkbox_image'], width=Inches(4))
                    except Exception as e:
                        p = doc.add_paragraph()
                        p.add_run(f'Error loading checkbox image: {str(e)}').italic = True
                
                doc.add_paragraph()  # Spacing between steps
            
            doc.add_paragraph()
        
        # Captured Images
        if images:
            doc.add_heading(f'Captured Images ({len(images)})', level=2)
            
            for idx, img_data in enumerate(images, 1):
                # Handle both old format (string path) and new format (dict with metadata)
                if isinstance(img_data, dict):
                    img_path = img_data['path']
                    camera = img_data.get('camera', 'Unknown')
                    notes = img_data.get('notes', '')
                    media_type = img_data.get('type', 'image')
                    step_info = img_data.get('step_info', '')
                    markers = img_data.get('markers', [])
                else:
                    # Legacy format - just a path string
                    img_path = img_data
                    camera = 'Unknown'
                    notes = ''
                    media_type = 'image'
                    step_info = ''
                    markers = []
                
                if os.path.exists(img_path):
                    # Check if this is a video file
                    is_video = media_type == 'video' or img_path.lower().endswith(('.avi', '.mp4', '.mov', '.mkv'))
                    
                    if is_video:
                        # For videos, just add a note
                        p = doc.add_paragraph()
                        p.add_run(f'Video {idx}: ').bold = True
                        p.add_run(os.path.basename(img_path))
                        
                        p = doc.add_paragraph()
                        p.add_run('Camera: ').italic = True
                        p.add_run(camera)
                        
                        p = doc.add_paragraph()
                        p.add_run('(Video file - not embedded in report)').italic = True
                        
                        if notes:
                            p = doc.add_paragraph()
                            p.add_run('Notes: ').bold = True
                            p.add_run(notes)
                        
                        # Add marker notes if present
                        marker_notes = [m for m in markers if m.get('note', '').strip()]
                        if marker_notes:
                            p = doc.add_paragraph()
                            p.add_run('Annotations:').bold = True
                            for m in marker_notes:
                                p = doc.add_paragraph(style='List Bullet')
                                p.add_run(f"{m['label']}: {m['note']}")
                        
                        if step_info:
                            p = doc.add_paragraph()
                            p.add_run('Step: ').italic = True
                            p.add_run(step_info)
                        
                        doc.add_paragraph()
                    else:
                        # For images, embed them
                        p = doc.add_paragraph()
                        p.add_run(f'Image {idx}: ').bold = True
                        p.add_run(os.path.basename(img_path))
                        
                        p = doc.add_paragraph()
                        p.add_run('Camera: ').italic = True
                        p.add_run(camera)
                        
                        if notes:
                            p = doc.add_paragraph()
                            p.add_run('Notes: ').bold = True
                            p.add_run(notes)
                        
                        # Add marker notes if present
                        marker_notes = [m for m in markers if m.get('note', '').strip()]
                        if marker_notes:
                            p = doc.add_paragraph()
                            p.add_run('Annotations:').bold = True
                            for m in marker_notes:
                                p = doc.add_paragraph(style='List Bullet')
                                p.add_run(f"{m['label']}: {m['note']}")
                        
                        if step_info:
                            p = doc.add_paragraph()
                            p.add_run('Step: ').italic = True
                            p.add_run(step_info)
                        
                        try:
                            # Add image (scaled to fit page width - 6 inches)
                            doc.add_picture(img_path, width=Inches(6))
                        except Exception as e:
                            # If image can't be loaded, show error message
                            p = doc.add_paragraph()
                            p.add_run(f'Error loading image: {str(e)}').italic = True
                        
                        doc.add_paragraph()
        else:
            doc.add_paragraph('No images captured')
        
        # Save document
        doc.save(filepath)
        return filepath


def create_simple_docx_report(serial_number, description, images, output_dir="output/reports"):
    """Convenience function to quickly generate a simple DOCX report.
    
    Args:
        serial_number: Serial number or identifier
        description: Job description
        images: List of image file paths OR list of dicts with {path, camera, notes}
        output_dir: Output directory for report
        
    Returns:
        Path to generated DOCX
    """
    generator = DOCXReportGenerator(output_dir)
    return generator.generate_report(serial_number, description, images)
