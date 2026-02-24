"""PDF report generator for QC and maintenance workflows."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib import colors
from datetime import datetime
import os


class PDFReportGenerator:
    """Generate PDF reports for QC and maintenance sessions."""
    
    def __init__(self, output_dir="output/reports"):
        """Initialize PDF generator.
        
        Args:
            output_dir: Directory to save generated reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Create custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12
        ))
    
    def generate_report(self, serial_number, description, images, mode_name="General Capture", 
                       workflow_name=None, checklist_data=None):
        """Generate a PDF report.
        
        Args:
            serial_number: Serial number or identifier
            description: Job description
            images: List of image file paths to include
            mode_name: Name of the mode used
            workflow_name: Optional workflow name (for Mode 2/3)
            checklist_data: Optional list of checklist items with status
            
        Returns:
            Path to generated PDF file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        serial = serial_number if serial_number else "unknown"
        filename = f"{serial}_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        
        # Title - determine report type based on mode_name
        if "Mode 1" in mode_name or "General" in mode_name or "Capture" in mode_name:
            report_title = "Emtech EOAT Report - Inspection"
        elif "Mode 2" in mode_name or "QC" in mode_name:
            report_title = "Emtech EOAT Report - QC"
        elif "Mode 3" in mode_name or "Maintenance" in mode_name:
            report_title = "Emtech EOAT Report - Maintenance/Repair"
        else:
            report_title = "Emtech EOAT Report - Inspection"
        
        title = Paragraph(report_title, self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.3*inch))
        
        # Session Information
        story.append(Paragraph("Session Information", self.styles['SectionHeader']))
        
        # Basic info table (without description)
        info_data = [
            ["Serial Number:", serial_number if serial_number else "N/A"],
            ["Mode:", mode_name],
            ["Date/Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        ]
        
        if workflow_name:
            info_data.append(["Workflow:", workflow_name])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Description as separate section (can span multiple pages)
        if description:
            story.append(Paragraph("<b>Description:</b>", self.styles['Normal']))
            story.append(Spacer(1, 0.05*inch))
            desc_paragraph = Paragraph(description, self.styles['Normal'])
            story.append(desc_paragraph)
        
        story.append(Spacer(1, 0.3*inch))
        
        # Procedure Summary (if provided)
        if checklist_data:
            story.append(Paragraph("Procedure Summary", self.styles['SectionHeader']))
            
            summary_table_data = [["Step", "Status"]]
            for item in checklist_data:
                if item.get('has_pass_fail', False):
                    status = "✓ Pass" if item.get('passed', False) else "✗ Fail"
                else:
                    status = "✓ Complete"
                summary_table_data.append([item['name'], status])
            
            summary_table = Table(summary_table_data, colWidths=[4*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Checklist (if provided)
        if checklist_data:
            story.append(Paragraph("Procedure Steps", self.styles['SectionHeader']))
            
            for item in checklist_data:
                # Step name and status
                if item.get('has_pass_fail', False):
                    status = "✓ Pass" if item.get('passed', False) else "✗ Fail"
                    status_color = colors.HexColor('#4CAF50') if item.get('passed', False) else colors.HexColor('#F44336')
                else:
                    status = "✓ Complete"
                    status_color = colors.HexColor('#81C784')  # Light green
                
                step_table_data = [[item['name'], status]]
                step_table = Table(step_table_data, colWidths=[4*inch, 2*inch])
                step_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
                    ('TEXTCOLOR', (0, 0), (0, 0), colors.whitesmoke),
                    ('TEXTCOLOR', (1, 0), (1, 0), status_color if item.get('has_pass_fail', False) else colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(step_table)
                
                # Add description if present
                if item.get('description'):
                    desc_para = Paragraph(f"<i>{item['description'][:200]}...</i>" if len(item['description']) > 200 else f"<i>{item['description']}</i>", 
                                        self.styles['Normal'])
                    story.append(Spacer(1, 0.05*inch))
                    story.append(desc_para)
                
                # Add checkbox image if present
                if item.get('checkbox_image') and os.path.exists(item['checkbox_image']):
                    story.append(Spacer(1, 0.1*inch))
                    story.append(Paragraph("<b>Reference Image (Inspection Points):</b>", self.styles['Normal']))
                    story.append(Spacer(1, 0.05*inch))
                    try:
                        checkbox_img = Image(item['checkbox_image'], width=4*inch, height=3*inch, kind='proportional')
                        story.append(checkbox_img)
                    except Exception as e:
                        error_msg = Paragraph(f"<i>Error loading reference image: {str(e)}</i>", self.styles['Normal'])
                        story.append(error_msg)
                
                # Add captured images for this step
                step_number = item.get('step_number')
                if step_number and images:
                    step_images = [img for img in images if isinstance(img, dict) and img.get('step') == step_number]
                    
                    if step_images:
                        story.append(Spacer(1, 0.1*inch))
                        story.append(Paragraph(f"<b>Captured Images ({len(step_images)}):</b>", self.styles['Normal']))
                        story.append(Spacer(1, 0.05*inch))
                        
                        for img_data in step_images:
                            img_path = img_data['path']
                            camera = img_data.get('camera', 'Unknown')
                            notes = img_data.get('notes', '')
                            markers = img_data.get('markers', [])
                            
                            if os.path.exists(img_path):
                                caption_text = f"<i>Camera: {camera}</i>"
                                if notes:
                                    caption_text += f"<br/><b>Notes:</b> {notes}"
                                
                                marker_notes = [m for m in markers if m.get('note', '').strip()]
                                if marker_notes:
                                    caption_text += "<br/><b>Annotations:</b>"
                                    for m in marker_notes:
                                        caption_text += f"<br/>  • {m['label']}: {m['note']}"
                                
                                caption = Paragraph(caption_text, self.styles['Normal'])
                                story.append(caption)
                                story.append(Spacer(1, 0.05*inch))
                                
                                try:
                                    img = Image(img_path, width=4*inch, height=3*inch, kind='proportional')
                                    story.append(img)
                                except Exception as e:
                                    error_msg = Paragraph(f"<i>Error loading image: {str(e)}</i>", self.styles['Normal'])
                                    story.append(error_msg)
                                
                                story.append(Spacer(1, 0.15*inch))
                
                story.append(Spacer(1, 0.3*inch))
            
            story.append(Spacer(1, 0.2*inch))
        
        # Captured Images (only for Mode 1 - no workflow)
        elif images:
            story.append(Paragraph(f"Captured Images ({len(images)})", self.styles['SectionHeader']))
            story.append(Spacer(1, 0.2*inch))
            
            for idx, img_data in enumerate(images, 1):
                # Handle both old format (string path) and new format (dict with metadata)
                if isinstance(img_data, dict):
                    img_path = img_data['path']
                    camera = img_data.get('camera', 'Unknown')
                    notes = img_data.get('notes', '')
                    media_type = img_data.get('type', 'image')
                    markers = img_data.get('markers', [])
                else:
                    # Legacy format - just a path string
                    img_path = img_data
                    camera = 'Unknown'
                    notes = ''
                    media_type = 'image'
                    markers = []
                
                if os.path.exists(img_path):
                    # Check if this is a video file
                    is_video = media_type == 'video' or img_path.lower().endswith(('.avi', '.mp4', '.mov', '.mkv'))
                    
                    if is_video:
                        # For videos, just add a note that video was recorded
                        caption_text = f"<b>Video {idx}</b>: {os.path.basename(img_path)}<br/>"
                        caption_text += f"<i>Camera: {camera}</i><br/>"
                        caption_text += "<i>(Video file - not embedded in report)</i>"
                        if notes:
                            caption_text += f"<br/><b>Notes:</b> {notes}"
                        
                        # Add marker notes if present
                        marker_notes = [m for m in markers if m.get('note', '').strip()]
                        if marker_notes:
                            caption_text += "<br/><b>Annotations:</b>"
                            for m in marker_notes:
                                caption_text += f"<br/>  • {m['label']}: {m['note']}"
                        
                        caption = Paragraph(caption_text, self.styles['Normal'])
                        story.append(caption)
                        story.append(Spacer(1, 0.3*inch))
                    else:
                        # For images, embed them in the report
                        caption_text = f"<b>Image {idx}</b>: {os.path.basename(img_path)}<br/>"
                        caption_text += f"<i>Camera: {camera}</i>"
                        if notes:
                            caption_text += f"<br/><b>Notes:</b> {notes}"
                        
                        # Add marker notes if present
                        marker_notes = [m for m in markers if m.get('note', '').strip()]
                        if marker_notes:
                            caption_text += "<br/><b>Annotations:</b>"
                            for m in marker_notes:
                                caption_text += f"<br/>  • {m['label']}: {m['note']}"
                        
                        caption = Paragraph(caption_text, self.styles['Normal'])
                        story.append(caption)
                        story.append(Spacer(1, 0.1*inch))
                        
                        try:
                            # Add image (scaled to fit page width)
                            img = Image(img_path, width=6*inch, height=4.5*inch, kind='proportional')
                            story.append(img)
                        except Exception as e:
                            # If image can't be loaded, show error message
                            error_msg = Paragraph(f"<i>Error loading image: {str(e)}</i>", self.styles['Normal'])
                            story.append(error_msg)
                        
                        story.append(Spacer(1, 0.3*inch))
                        
                        # Page break after every 2 images to avoid crowding
                        if idx % 2 == 0 and idx < len(images):
                            story.append(PageBreak())
        else:
            story.append(Paragraph("No images captured", self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return filepath


def create_simple_report(serial_number, description, images, output_dir="output/reports"):
    """Convenience function to quickly generate a simple report.
    
    Args:
        serial_number: Serial number or identifier
        description: Job description
        images: List of image file paths OR list of dicts with {path, camera, notes}
        output_dir: Output directory for report
        
    Returns:
        Path to generated PDF
    """
    generator = PDFReportGenerator(output_dir)
    return generator.generate_report(serial_number, description, images)
