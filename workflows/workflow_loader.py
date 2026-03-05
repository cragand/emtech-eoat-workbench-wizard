"""Workflow loader for QC and maintenance processes."""
import json
import os
from typing import List, Dict, Optional
from pathlib import Path


class WorkflowLoader:
    """Loads and manages workflow definitions."""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.base_path = Path(base_path)
        self.qc_workflows_path = self.base_path / "workflows" / "qc_workflows"
        self.maintenance_workflows_path = self.base_path / "workflows" / "maintenance_workflows"
        self.qc_images_path = self.base_path / "resources" / "qc_reference_images"
        self.maintenance_images_path = self.base_path / "resources" / "maintenance_reference_images"
    
    def get_qc_workflows(self) -> List[Dict]:
        """Get all available QC workflows."""
        return self._load_workflows_from_directory(self.qc_workflows_path)
    
    def get_maintenance_workflows(self) -> List[Dict]:
        """Get all available maintenance workflows."""
        return self._load_workflows_from_directory(self.maintenance_workflows_path)
    
    def load_workflow(self, workflow_path: str) -> Optional[Dict]:
        """Load a specific workflow by path."""
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load workflow {workflow_path}: {e}")
            return None
    
    def get_reference_image_path(self, workflow_type: str, image_filename: str) -> Optional[Path]:
        """Get full path to a reference image."""
        if workflow_type == "qc":
            image_path = self.qc_images_path / image_filename
        elif workflow_type == "maintenance":
            image_path = self.maintenance_images_path / image_filename
        else:
            return None
        
        return image_path if image_path.exists() else None
    
    def _load_workflows_from_directory(self, directory: Path) -> List[Dict]:
        """Load all JSON workflows from a directory."""
        workflows = []
        
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            return workflows
        
        for json_file in directory.glob("*.json"):
            workflow = self.load_workflow(str(json_file))
            if workflow:
                workflow['_file_path'] = str(json_file)
                workflows.append(workflow)
        
        return workflows
