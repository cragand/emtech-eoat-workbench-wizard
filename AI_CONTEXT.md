# AI Context: Emtech EoAT Workbench Wizard

## Project Overview
This is a Python-based quality control and maintenance application designed for manufacturing/lab environments. It provides guided workflows with camera integration for documentation and reporting.

## Application Name
- **Full Name**: Emtech EoAT Workbench Wizard
- **Abbreviation**: EEWW
- **Previous Name**: Emtech EoAT Cam Viewer (legacy)

## Core Purpose
- Perform systematic quality control checks on manufactured components
- Guide technicians through maintenance/repair procedures
- Capture images/video during processes for documentation
- Generate PDF/DOCX reports with captured media and workflow results
- Track work by serial number (optional) with QR code scanning support

## Technology Stack
- **GUI Framework**: PyQt5 (Python 3.7 compatible)
- **Camera**: OpenCV (webcam and USB borescope only - NO Basler/pypylon)
- **QR Scanning**: pyzbar (passive background scanning, optional)
- **Reporting**: reportlab 3.6.x (PDF), python-docx (DOCX generation)
- **Image Processing**: Pillow, OpenCV
- **Video**: MP4 codec with H264 encoding

## Application Architecture

### Three Operating Modes
1. **Mode 1: General Image Capture** - Free-form image/video capture with any camera
2. **Mode 2: QC Process** - Guided quality control with step-by-step workflows
3. **Mode 3: Maintenance/Repair** - Guided maintenance procedures

### Key Components

#### Camera System (`camera/`)
- **camera_interface.py** - Abstract base class for camera implementations
- **opencv_camera.py** - OpenCV camera implementation (webcam/borescope)
- **camera_manager.py** - Discovers and manages available cameras
- Uses OpenCV VideoCapture for all camera access

#### GUI (`gui/`)
- **mode_selection.py** - Initial screen for mode selection and job info entry
- **mode1_capture.py** - General capture interface with annotations
- **workflow_selection.py** - Workflow selection screen for Mode 2/3
- **workflow_execution.py** - Step-by-step workflow execution with split-screen view
- **workflow_editor.py** - Password-protected workflow editor with unsaved changes protection
- **annotatable_preview.py** - Camera preview widget with annotation system

#### Annotation System
- Rotatable arrow markers with sequential labels (A, B, C...)
- Variable arrow length (Shift+Scroll to adjust, max 300px)
- Left-click to add, drag to move, scroll to rotate, right-click to remove
- Markers saved with images and embedded in videos
- Uses relative coordinates for resolution independence

#### QR Code Scanner (`qr_scanner.py`)
- Runs passively in background thread when camera is active
- Automatically detects and reads QR codes
- Appends scanned data to serial number field (or sets it if empty)
- Works across all modes without user intervention

#### Workflow System (`workflows/`)
- JSON-based workflow definitions
- `qc_workflows/` - Quality control process definitions
- `maintenance_workflows/` - Maintenance procedure definitions
- Each step can specify:
  - Instructions and reference images
  - Inspection checkboxes (bright amber/yellow)
  - Photo/annotation/pass-fail requirements
  - Step validation before proceeding

#### Workflow Editor
- Password-protected (default: "admin")
- Create, edit, delete workflows
- Add/edit/delete/reorder steps
- Place inspection checkboxes on reference images
- Unsaved changes protection with Save/Discard/Cancel prompt
- Tracks changes via JSON state comparison

#### Reports (`reports/`)
- **report_generator.py** - Factory for PDF/DOCX generation
- **pdf_generator.py** - PDF report generation with reportlab
- **docx_generator.py** - DOCX report generation with python-docx
- Supports session info, images, videos, checklists, and workflow data
- Professional layout with tables, styling, and automatic pagination
- Procedure summary table with step status (Complete/Pass/Fail)
- Reference images with inspection checkboxes in reports

#### Progress Save/Resume
- Automatic progress saving during workflow execution
- Resume incomplete workflows from main menu
- Delete selected progress files
- Auto-cleanup of progress files older than 30 days
- Preserves captured media, annotations, and step states

#### Video Recording
- MP4 format with H264 codec
- Recording indicator with elapsed timer
- Annotation overlays embedded in video
- Videos saved in progress and included in reports
- Relative file paths in reports for portability

#### Output Structure
```
output/
├── captured_images/
│   └── {serial_number}/     # Images organized by serial number
├── reports/                  # Generated PDF/DOCX reports
└── progress/                 # Workflow progress files (auto-cleanup 30+ days)
```

## Serial Number Handling
- **Optional** - User can proceed without entering a serial number
- Can be manually entered at startup
- Can be automatically populated by QR code scanner
- Multiple QR scans append to existing serial number with underscore separator
- Used for organizing output files and in report generation
- Defaults to "unknown" for file organization if not provided

## Current Implementation Status

### ✅ Fully Implemented
- All three operating modes (Mode 1, 2, 3)
- Mode selection screen with optional serial number
- Camera discovery and management (OpenCV only)
- Multi-camera support (auto-discovery)
- Passive QR code scanning across all modes (optional, graceful degradation)
- Annotation system with variable-length rotatable arrows
- Image capture with annotations
- Video recording with annotation overlays (MP4/H264)
- Workflow JSON parsing and execution
- Step-by-step workflow execution with validation
- Split-screen view (instructions/reference | live camera)
- Comparison window with capture/record on live camera side
- Reference image display with fullsize resizable view
- Inspection checkboxes on reference images (bright amber/yellow)
- Checkbox state preservation and syncing
- Step requirements validation (photo/annotations/pass-fail)
- Workflow editor with password protection
- Unsaved changes protection in editor
- Progress save/resume functionality
- Progress file management (delete selected, auto-cleanup)
- PDF and DOCX report generation
- Procedure summary tables with status indicators
- Comprehensive logging and error handling
- File organization by serial number

## Important Design Decisions

### Camera Support
- **ONLY OpenCV cameras** - No Basler/pypylon support
- Supports standard USB webcams and borescope cameras
- Camera discovery checks indices 0-4 for available devices
- DirectShow backend on Windows for fast initialization

### QR Scanner Behavior
- Runs in separate thread to avoid blocking UI
- Scans every 100ms when camera is active
- Only emits signal when NEW QR code detected (prevents duplicates)
- Automatically stops when camera disconnects or mode closes

### Annotation System Design
- Relative coordinates (0.0-1.0) for resolution independence
- Markers embedded in saved images (permanent)
- Markers overlaid on videos in real-time during recording
- Variable arrow length (50-300px) adjustable with Shift+Scroll
- Sequential labeling (A, B, C...) with automatic reordering on deletion

### Video Recording
- MP4 container with H264 codec for compatibility
- Annotations rendered as overlay during recording
- Recording indicator with elapsed timer in UI
- Videos saved in progress and included in final reports

### Workflow Execution
- Split-screen layout: instructions/reference on left, live camera on right
- Step validation before allowing progression
- Automatic step failure if inspection checkboxes incomplete
- Progress auto-saved after each step completion
- Comparison window allows capture/record on live camera side

### File Naming Convention
- Format: `{serial_number}_{timestamp}.{ext}`
- Timestamp: `YYYYMMDD_HHMMSS`
- If no serial number: uses "unknown" as prefix

### Progress Management
- Progress files saved as JSON in `output/progress/`
- Auto-cleanup of files older than 30 days on startup
- Resume dialog shows file list with delete functionality
- Progress includes all captured media paths and step states

## Development Guidelines

### Modifying Workflows
- Edit JSON files in `workflows/qc_workflows/` or `workflows/maintenance_workflows/`
- Or use the built-in workflow editor (password: "admin")
- Workflow editor has unsaved changes protection
- Changes tracked via JSON state comparison

### Adding Workflow Steps
- Each step requires: title, instructions
- Optional: reference_image, inspection checkboxes, requirements
- Requirements: require_photo, require_annotations, require_pass_fail
- Checkboxes placed via editor's "Place Checkboxes" feature

### Report Customization
- Reports support both PDF and DOCX formats
- Format selected by user at report generation time
- Procedure summary table shows all steps with status indicators
- Status types: Complete (light green), Pass (green), Fail (red)
- Videos shown with relative paths for portability

### Extending Annotation System
- Markers stored as list of dicts: {label, x, y, angle, length}
- Coordinates are relative (0.0-1.0) to image dimensions
- Drawing handled in `annotatable_preview.py`
- Video overlay rendering in `workflow_execution.py`

## Common Pitfall Warnings
- ⚠️ Do NOT add pypylon or Basler camera support
- ⚠️ Serial number is OPTIONAL - never require it
- ⚠️ QR scanner must run in separate thread (don't block UI)
- ⚠️ Always stop QR scanner thread in cleanup/closeEvent
- ⚠️ Camera indices may not be sequential - test each index
- ⚠️ Use relative coordinates for annotations (resolution independence)
- ⚠️ Always validate step requirements before allowing progression
- ⚠️ Clean up video writers properly to avoid corrupted files
- ⚠️ Workflow editor password is hardcoded - change in workflow_selection.py

## Testing Considerations
- Test with no cameras connected (graceful degradation)
- Test with multiple cameras (selection should work)
- Test QR scanning with various QR code formats
- Test with and without serial numbers
- Verify file organization when serial number changes mid-session
- Test workflow resume after interruption
- Test progress file auto-cleanup (30+ days)
- Test unsaved changes protection in workflow editor
- Test video recording with annotations
- Test report generation in both PDF and DOCX formats
- Test inspection checkbox state preservation in fullsize view

## Recent Enhancements (2026-02-26)
- Unsaved changes protection in workflow editor
- Variable arrow length (Shift+Scroll, 50-300px max)
- MP4 video recording with annotation overlays
- Resume incomplete workflow feature
- Progress file management with auto-cleanup
- Checkbox state syncing in fullsize reference view
- Improved UI/UX (button reordering, color coding)
- Comprehensive logging and error handling
