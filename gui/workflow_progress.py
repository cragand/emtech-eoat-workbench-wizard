"""Workflow progress save/load/clear functions."""
import os
import json
from datetime import datetime
from logger_config import get_logger

logger = get_logger(__name__)


def save_workflow_progress(output_dir, workflow_path, current_step, step_results,
                           step_checkbox_states, captured_images, recorded_videos,
                           serial_number, technician, description):
    """Save current workflow progress to JSON file.
    
    Returns:
        True on success, False on failure.
    """
    try:
        progress_file = os.path.join(output_dir, "_workflow_progress.json")
        progress_data = {
            'workflow_path': workflow_path,
            'current_step': current_step,
            'step_results': step_results,
            'step_checkbox_states': step_checkbox_states,
            'captured_images': captured_images,
            'recorded_videos': recorded_videos,
            'serial_number': serial_number,
            'technician': technician,
            'description': description
        }
        # Atomic write: write to temp file then rename to prevent corruption
        tmp_file = progress_file + ".tmp"
        with open(tmp_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
        os.replace(tmp_file, progress_file)
        return True
    except Exception as e:
        logger.error(f"Error saving progress: {e}", exc_info=True)
        return False


def load_workflow_progress(output_dir, workflow_path):
    """Load saved workflow progress if it exists and matches the workflow.
    
    Returns:
        Dict with progress data, or None if no valid progress found.
        Returns 'corrupted' string if file exists but is unreadable.
    """
    progress_file = os.path.join(output_dir, "_workflow_progress.json")

    if not os.path.exists(progress_file):
        return None

    try:
        # Check if progress file is older than 30 days
        file_age_days = (datetime.now().timestamp() - os.path.getmtime(progress_file)) / 86400
        if file_age_days > 30:
            logger.info(f"Progress file is {file_age_days:.1f} days old, removing")
            os.remove(progress_file)
            return None

        with open(progress_file, 'r') as f:
            progress_data = json.load(f)

        if not isinstance(progress_data, dict):
            raise ValueError("Progress file is not a valid JSON object")

        if progress_data.get('workflow_path') != workflow_path:
            logger.warning("Progress file is for a different workflow, ignoring")
            return None

        return progress_data

    except json.JSONDecodeError as e:
        logger.error(f"Progress file is corrupted (invalid JSON): {e}")
        try:
            os.remove(progress_file)
        except OSError:
            pass
        return 'corrupted'
    except Exception as e:
        logger.error(f"Error loading progress: {e}", exc_info=True)
        try:
            os.remove(progress_file)
        except OSError:
            pass
        return 'corrupted'


def clear_workflow_progress(output_dir):
    """Delete the progress file."""
    progress_file = os.path.join(output_dir, "_workflow_progress.json")
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
            logger.info("Progress file cleared")
    except Exception as e:
        logger.error(f"Error clearing progress: {e}", exc_info=True)
