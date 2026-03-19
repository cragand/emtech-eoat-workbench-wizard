"""Generate printable workflow instruction documents as PDF."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib import colors
from datetime import datetime
import os
import cv2
import tempfile

from logger_config import get_logger

logger = get_logger(__name__)


def render_checkboxes_on_image(image_path, checkboxes):
    """Render inspection checkboxes onto a reference image.
    
    Draws unchecked amber/yellow checkbox squares matching the style
    used in the workflow execution screen.
    
    Args:
        image_path: Path to the reference image file.
        checkboxes: List of dicts with 'x' and 'y' keys (relative 0-1 coords).
        
    Returns:
        Path to a temporary image file with checkboxes drawn, or None on failure.
    """
    if not os.path.exists(image_path):
        return None
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        h, w = img.shape[:2]
        for cb in checkboxes:
            x = int(cb['x'] * w)
            y = int(cb['y'] * h)
            color = (7, 193, 255)  # BGR of #FFC107 (amber)
            # Draw border
            cv2.rectangle(img, (x - 16, y - 16), (x + 16, y + 16), color, 3)
            # Semi-transparent white fill (unchecked appearance)
            overlay = img.copy()
            cv2.rectangle(overlay, (x - 16, y - 16), (x + 16, y + 16), (255, 255, 255), -1)
            cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
        
        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        cv2.imwrite(tmp.name, img)
        return tmp.name
    except Exception as e:
        logger.error(f"Error rendering checkboxes on image: {e}")
        return None


def generate_workflow_instructions(workflow, output_dir="output/reports"):
    """Generate a printable PDF instruction document from a workflow definition.
    
    Args:
        workflow: Workflow dict with 'name', 'description', and 'steps'.
        output_dir: Directory to save the generated PDF.
        
    Returns:
        Path to the generated PDF file, or None on failure.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    workflow_name = workflow.get('name', 'Workflow')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in workflow_name).strip()
    filename = f"Instructions_{safe_name}_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='DocTitle', parent=styles['Heading1'],
        fontSize=22, textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name='DocSubtitle', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#555555'),
        spaceAfter=20, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name='StepTitle', parent=styles['Heading2'],
        fontSize=14, textColor=colors.HexColor('#333333'),
        spaceAfter=8, spaceBefore=4
    ))
    styles.add(ParagraphStyle(
        name='Instructions', parent=styles['Normal'],
        fontSize=10, leading=14, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name='Requirements', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#666666'),
        spaceAfter=6, leftIndent=12
    ))
    
    temp_files = []
    
    try:
        doc = SimpleDocTemplate(filepath, pagesize=letter,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        
        # Title
        story.append(Paragraph(f"Workflow Instructions: {workflow_name}", styles['DocTitle']))
        
        description = workflow.get('description', '')
        if description:
            story.append(Paragraph(description, styles['DocSubtitle']))
        
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles['DocSubtitle']
        ))
        story.append(Spacer(1, 0.2*inch))
        
        steps = workflow.get('steps', [])
        
        # Overview table
        if steps:
            cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, leading=11)
            header_style = ParagraphStyle('HeaderCell', parent=cell_style, textColor=colors.whitesmoke, fontName='Helvetica-Bold')
            overview_data = [
                [Paragraph("#", header_style), Paragraph("Step", header_style), Paragraph("Requirements", header_style)]
            ]
            for i, step in enumerate(steps):
                reqs = _get_requirements_list(step)
                req_text = ", ".join(reqs) if reqs else "None"
                overview_data.append([
                    str(i + 1),
                    Paragraph(step.get('title', f'Step {i+1}'), cell_style),
                    Paragraph(req_text, cell_style)
                ])
            
            overview_table = Table(overview_data, colWidths=[0.4*inch, 3.1*inch, 2.5*inch])
            overview_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
            ]))
            story.append(overview_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Detailed steps
        for i, step in enumerate(steps):
            # Page break before each step (except first)
            if i > 0:
                story.append(PageBreak())
            
            title = step.get('title', f'Step {i + 1}')
            story.append(Paragraph(f"Step {i + 1}: {title}", styles['StepTitle']))
            
            # Separator line
            line_table = Table([['']],  colWidths=[6*inch])
            line_table.setStyle(TableStyle([
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#77C25E')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(line_table)
            story.append(Spacer(1, 0.1*inch))
            
            # Instructions text
            instructions = step.get('instructions', step.get('description', ''))
            if instructions:
                # Convert newlines to <br/> for reportlab
                formatted = instructions.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                formatted = formatted.replace('\n', '<br/>')
                story.append(Paragraph(formatted, styles['Instructions']))
            
            # Requirements
            reqs = _get_requirements_list(step)
            if reqs:
                req_text = "  •  ".join(reqs)
                story.append(Paragraph(f"<b>Requirements:</b>  {req_text}", styles['Requirements']))
                story.append(Spacer(1, 0.1*inch))
            
            # Reference image with checkboxes
            ref_image = step.get('reference_image', '')
            checkboxes = step.get('inspection_checkboxes', [])
            is_overlay = step.get('transparent_overlay', False)
            
            if ref_image and os.path.exists(ref_image):
                if checkboxes and not is_overlay:
                    # Render checkboxes onto the image
                    composited = render_checkboxes_on_image(ref_image, checkboxes)
                    if composited:
                        temp_files.append(composited)
                        img_to_use = composited
                    else:
                        img_to_use = ref_image
                else:
                    img_to_use = ref_image
                
                label = "Reference Image (with Inspection Points):" if checkboxes else "Reference Image:"
                if is_overlay:
                    label = "Overlay Image:"
                story.append(Paragraph(f"<b>{label}</b>", styles['Normal']))
                story.append(Spacer(1, 0.05*inch))
                
                try:
                    img = Image(img_to_use, width=5*inch, height=3.75*inch, kind='proportional')
                    story.append(img)
                except Exception as e:
                    story.append(Paragraph(f"<i>Error loading image: {e}</i>", styles['Normal']))
                
                if checkboxes:
                    story.append(Spacer(1, 0.05*inch))
                    story.append(Paragraph(
                        f"<i>{len(checkboxes)} inspection point(s) — all must be checked during execution</i>",
                        styles['Requirements']
                    ))
            elif ref_image and not os.path.exists(ref_image):
                story.append(Paragraph(
                    f"<i>Reference image not found: {os.path.basename(ref_image)}</i>",
                    styles['Requirements']
                ))
            
            # Reference video note
            ref_video = step.get('reference_video', '')
            if ref_video:
                video_name = os.path.basename(ref_video)
                story.append(Spacer(1, 0.05*inch))
                story.append(Paragraph(
                    f"<b>Reference Video:</b> {video_name}",
                    styles['Requirements']
                ))
        
        doc.build(story)
        logger.info(f"Generated workflow instructions: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error generating workflow instructions PDF: {e}")
        return None
    finally:
        # Clean up temp files
        for f in temp_files:
            try:
                os.remove(f)
            except OSError:
                pass


def _get_requirements_list(step):
    """Extract human-readable requirements from a workflow step."""
    reqs = []
    if step.get('require_photo') or step.get('requires_photo'):
        reqs.append("📸 Photo capture")
    if step.get('require_annotations'):
        reqs.append("✏️ Annotations")
    if step.get('require_pass_fail'):
        reqs.append("✓✗ Pass/Fail judgment")
    if step.get('require_barcode_scan'):
        reqs.append("📱 Barcode scan")
    if step.get('inspection_checkboxes'):
        reqs.append(f"☐ {len(step['inspection_checkboxes'])} inspection point(s)")
    return reqs
