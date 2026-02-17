"""Unified report generation - creates both PDF and DOCX."""
from .pdf_generator import PDFReportGenerator
from .docx_generator import DOCXReportGenerator


def generate_reports(serial_number, description, images, mode_name="General Capture",
                    workflow_name=None, checklist_data=None, output_dir="output/reports"):
    """Generate both PDF and DOCX reports.
    
    Args:
        serial_number: Serial number or identifier
        description: Job description
        images: List of image file paths OR list of dicts with {path, camera, notes}
        mode_name: Name of the mode used
        workflow_name: Optional workflow name (for Mode 2/3)
        checklist_data: Optional list of checklist items with status
        output_dir: Output directory for reports
        
    Returns:
        Tuple of (pdf_path, docx_path)
    """
    pdf_gen = PDFReportGenerator(output_dir)
    docx_gen = DOCXReportGenerator(output_dir)
    
    pdf_path = pdf_gen.generate_report(
        serial_number, description, images, mode_name, workflow_name, checklist_data
    )
    
    docx_path = docx_gen.generate_report(
        serial_number, description, images, mode_name, workflow_name, checklist_data
    )
    
    return pdf_path, docx_path
