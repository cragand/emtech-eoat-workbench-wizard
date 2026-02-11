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
        
        # Title
        title = Paragraph("Camera QC Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.3*inch))
        
        # Session Information
        story.append(Paragraph("Session Information", self.styles['SectionHeader']))
        
        info_data = [
            ["Serial Number:", serial_number if serial_number else "N/A"],
            ["Description:", description if description else "N/A"],
            ["Mode:", mode_name],
            ["Date/Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        ]
        
        if workflow_name:
            info_data.append(["Workflow:", workflow_name])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
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
        story.append(Spacer(1, 0.3*inch))
        
        # Checklist (if provided)
        if checklist_data:
            story.append(Paragraph("Checklist Results", self.styles['SectionHeader']))
            
            checklist_table_data = [["Item", "Status"]]
            for item in checklist_data:
                status = "✓ Pass" if item.get('passed', False) else "✗ Fail"
                checklist_table_data.append([item['name'], status])
            
            checklist_table = Table(checklist_table_data, colWidths=[4*inch, 2*inch])
            checklist_table.setStyle(TableStyle([
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
            story.append(checklist_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Captured Images
        if images:
            story.append(Paragraph(f"Captured Images ({len(images)})", self.styles['SectionHeader']))
            story.append(Spacer(1, 0.2*inch))
            
            for idx, img_path in enumerate(images, 1):
                if os.path.exists(img_path):
                    # Add image caption
                    caption = Paragraph(f"Image {idx}: {os.path.basename(img_path)}", 
                                      self.styles['Normal'])
                    story.append(caption)
                    story.append(Spacer(1, 0.1*inch))
                    
                    # Add image (scaled to fit page width)
                    img = Image(img_path, width=6*inch, height=4.5*inch, kind='proportional')
                    story.append(img)
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
        images: List of image file paths
        output_dir: Output directory for report
        
    Returns:
        Path to generated PDF
    """
    generator = PDFReportGenerator(output_dir)
    return generator.generate_report(serial_number, description, images)
