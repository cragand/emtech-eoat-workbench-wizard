"""Logging configuration for the camera QC application."""
import logging
import os
from datetime import datetime


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
    
    return logger


def get_logger(name):
    """Get a logger for a specific module."""
    return logging.getLogger(name)
