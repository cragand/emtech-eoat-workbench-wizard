"""Unified report generation - creates both PDF and DOCX."""
import os
import shutil
import tempfile
from logger_config import get_logger
from .pdf_generator import PDFReportGenerator
from .docx_generator import DOCXReportGenerator

logger = get_logger(__name__)


def _is_network_path(path):
    """Check if a path is likely a network/remote location."""
    abs_path = os.path.abspath(path)
    # UNC paths (Windows network shares)
    if abs_path.startswith("\\\\") or abs_path.startswith("//"):
        return True
    # Common network mount indicators on Linux
    for prefix in ("/mnt/", "/media/", "/net/", "/Volumes/"):
        if abs_path.startswith(prefix):
            return True
    return False


def generate_reports(serial_number, technician, description, images, mode_name="General Capture",
                    workflow_name=None, checklist_data=None, video_paths=None, barcode_scans=None, output_dir="output/reports"):
    """Generate both PDF and DOCX reports.
    
    For network/remote output directories, reports are generated locally first
    then copied to the target to avoid hangs on slow or unavailable shares.
    
    Args:
        serial_number: Serial number or identifier
        technician: Technician name
        description: Job description
        images: List of image file paths OR list of dicts with {path, camera, notes, barcode_scans}
        mode_name: Name of the mode used
        workflow_name: Optional workflow name (for Mode 2/3)
        checklist_data: Optional list of checklist items with status
        video_paths: Optional list of video file paths
        barcode_scans: Optional list of barcode scans {type, data, timestamp}
        output_dir: Output directory for reports
        
    Returns:
        Tuple of (pdf_path, docx_path)
    """
    use_staging = _is_network_path(output_dir)

    if use_staging:
        staging_dir = tempfile.mkdtemp(prefix="eeww_report_")
        gen_dir = staging_dir
        logger.info("Network output path detected, staging reports locally first: %s", staging_dir)
    else:
        gen_dir = output_dir

    pdf_gen = PDFReportGenerator(gen_dir)
    docx_gen = DOCXReportGenerator(gen_dir)
    
    pdf_path = pdf_gen.generate_report(
        serial_number, technician, description, images, mode_name, workflow_name, checklist_data, video_paths, barcode_scans
    )
    
    docx_path = docx_gen.generate_report(
        serial_number, technician, description, images, mode_name, workflow_name, checklist_data, video_paths, barcode_scans
    )

    if use_staging:
        os.makedirs(output_dir, exist_ok=True)
        final_pdf = final_docx = None
        try:
            if pdf_path and os.path.exists(pdf_path):
                final_pdf = os.path.join(output_dir, os.path.basename(pdf_path))
                shutil.copy2(pdf_path, final_pdf)
            if docx_path and os.path.exists(docx_path):
                final_docx = os.path.join(output_dir, os.path.basename(docx_path))
                shutil.copy2(docx_path, final_docx)
            logger.info("Reports copied to network path: %s", output_dir)
            pdf_path, docx_path = final_pdf, final_docx
        except OSError:
            logger.warning("Failed to copy reports to network path, keeping local copies", exc_info=True)
            # Return the local staging paths so the user still has their reports
        finally:
            # Clean up staging dir only if copy succeeded
            try:
                if final_pdf and final_docx:
                    shutil.rmtree(staging_dir, ignore_errors=True)
            except Exception:
                pass

    return pdf_path, docx_path
