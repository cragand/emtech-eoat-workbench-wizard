"""Logging configuration for the camera QC application."""
import logging
import glob
import os
import time
from datetime import datetime

LOG_RETENTION_DAYS = 30


def setup_logging():
    """Configure application-wide logging."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with date
    log_file = os.path.join(log_dir, f"camera_qc_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also print to console
        ]
    )
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Camera QC Application Started")
    logger.info("=" * 50)
    
    # Clean up old log files
    _cleanup_old_logs(log_dir, logger)
    
    return logger


def _cleanup_old_logs(log_dir, logger):
    """Delete log files older than LOG_RETENTION_DAYS."""
    cutoff = time.time() - (LOG_RETENTION_DAYS * 86400)
    removed = 0
    for log_path in glob.glob(os.path.join(log_dir, "camera_qc_*.log")):
        try:
            if os.path.getmtime(log_path) < cutoff:
                os.remove(log_path)
                removed += 1
        except OSError:
            pass
    if removed:
        logger.info(f"Cleaned up {removed} log file(s) older than {LOG_RETENTION_DAYS} days")


def get_logger(name):
    """Get a logger for a specific module."""
    return logging.getLogger(name)
