# Emtech EoAT Workbench Wizard

Quality control and maintenance application with guided workflows, camera integration, and annotation system.

## Quick Start (Windows)

**Easy Method - Double-click to run:**
1. Double-click `runEEWW.bat`
2. First run will automatically set up the environment (takes 1-2 minutes)
3. Subsequent runs launch immediately

## Quick Start (Linux)

**Easy Method - Run script:**
1. Make the script executable (first time only):
   ```bash
   chmod +x runEEWW.sh
   ```
2. Run the script:
   ```bash
   ./runEEWW.sh
   ```
3. First run will automatically set up the environment (takes 1-2 minutes)
4. Subsequent runs launch immediately

**Manual Method:**

## Setup

1. Create virtual environment:
```bash
python -m venv venv
```

2. Activate virtual environment:
- Windows: `venv\Scripts\activate`
- Linux: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python main.py
```

## Application Modes

### Mode 1: General Image Capture

Free-form capture mode for quick documentation.

**Features:**
- Live camera preview
- Multi-camera support (auto-detection)
- Image and video capture
- Annotation markers (rotatable arrows with labels)
- Per-image notes
- Optional QR code scanning
- Generate PDF reports

**How to use:**
1. Enter serial number (optional) and description
2. Select Mode 1 and click Start
3. Choose camera from dropdown
4. Add annotations by clicking on preview
   - Left-click: Add marker (A, B, C...)
   - Drag: Move marker
   - Scroll wheel: Rotate marker
   - Right-click: Remove marker
5. Add notes for each image (optional)
6. Click "Capture Image" to save
7. Click "Generate Report" when done

**Annotations:**
- Click on camera preview to place markers
- Markers are labeled sequentially (A, B, C...)
- Hover over marker and scroll to rotate
- Drag markers to reposition
- Reference markers in notes (e.g., "A: Defect on corner")

### Mode 2: QC Process

Guided quality control workflows with step-by-step instructions.

**Features:**
- Step-by-step workflow execution
- Split screen: Instructions/Reference | Camera view
- Required photo capture per step
- Required annotations per step
- Progress tracking
- Workflow completion checklist in report

**How to use:**
1. Enter serial number and description
2. Select Mode 2 and click Start
3. Choose a workflow from the list
4. Click "Start Workflow"
5. Follow instructions for each step
6. Capture required photos with annotations
7. Click "Next Step" to proceed (validates requirements)
8. Click "Finish Workflow" to complete
9. Generate report with checklist

**Step Requirements:**
- Some steps require photo capture before proceeding
- Some steps require annotations on photos
- Some steps require pass/fail marking
- Steps with inspection checkboxes automatically fail if not all checked
- System validates requirements before allowing next step

**Inspection Checkboxes:**
- Click checkboxes on reference image to mark inspection points
- All checkboxes must be checked for step to pass
- Checkboxes are bright amber/yellow for visibility
- Click "🔍 View Full Size" to see reference image in resizable window
- Checkbox states are saved and included in reports

### Mode 3: Maintenance/Repair

Guided maintenance procedures with documentation.

**Features:**
- Same as Mode 2, but for maintenance workflows
- Multi-step procedures
- Reference images for each step
- Documentation of maintenance process
- Completion checklist

**How to use:**
- Same as Mode 2, but select Mode 3

## Workflow Editor

Create and customize workflows for Mode 2 and Mode 3.

**Access:**
1. Select Mode 2 or Mode 3
2. Click "Edit Workflows" button
3. Enter password: `admin`

**Features:**
- Create new workflows
- Edit existing workflows
- Delete workflows
- Add/edit/delete steps
- Reorder steps (up/down arrows)
- Set step requirements

**Creating a Workflow:**
1. Click "New Workflow"
2. Enter workflow name and description
3. Click "Add Step" to add steps
4. For each step, configure:
   - Title
   - Instructions
   - Reference image (optional)
   - Inspection checkboxes (optional - click "Place Checkboxes" after selecting reference image)
   - Require photo capture (checkbox)
   - Require annotations (checkbox)
   - Require pass/fail marking (checkbox)
5. Use ↑↓ buttons to reorder steps
6. Click "Save Workflow"

**Editing a Workflow:**
1. Click on workflow in the list
2. Modify name, description, or steps
3. Click "Save Workflow"

**Step Editor:**
- **Title**: Short name for the step
- **Instructions**: Detailed instructions for the user
- **Reference Image**: Optional image to display alongside camera
- **Place Checkboxes**: Add inspection points on reference image (bright amber/yellow boxes)
- **Require Photo**: User must capture at least one photo
- **Require Annotations**: User must add markers to photos
- **Require Pass/Fail**: User must explicitly mark step as pass or fail

**Inspection Checkboxes:**
- Click on reference image to place checkboxes at inspection points
- Left-click: Add checkbox
- Right-click: Remove checkbox
- Checkboxes appear as bright amber/yellow squares
- During workflow execution, user clicks checkboxes to mark inspection complete
- Step automatically fails if not all checkboxes are checked

## Annotations

The annotation system allows you to mark specific features in images.

**Controls:**
- **Left-click**: Add marker at cursor position
- **Drag**: Move marker to new position
- **Scroll wheel**: Rotate marker (hover over marker first)
- **Right-click**: Remove marker
- **Clear Markers button**: Remove all markers

**Markers:**
- Labeled sequentially: A, B, C, D...
- Red arrows with white label circles
- Rotatable in any direction (0-360°)
- Saved with images
- Included in reports

**Usage Tips:**
- Add markers to highlight defects, features, or areas of interest
- Reference markers in notes: "A: Crack in corner, B: Surface scratch"
- Rotate markers to point in the appropriate direction
- Markers are permanently drawn on saved images

## PDF/DOCX Reports

Professional PDF and DOCX reports are generated with all captured data.

**Report Contents:**
- **Header**: Emtech EOAT Report - Inspection/QC/Maintenance
- **Session Information**: Serial number, description, date/time
- **Workflow Info**: Workflow name (Mode 2/3 only)
- **Procedure Summary**: Quick overview table of all steps and their status (Mode 2/3 only)
- **Procedure Steps**: Detailed view of each step with:
  - Step name and status (Complete/Pass/Fail)
  - Step description
  - Reference image with inspection checkboxes (if applicable)
  - Captured images with annotations and notes
- **Images**: All captured images with:
  - Camera source
  - Per-image notes
  - Annotation markers
  - Step context (Mode 2/3)

**Status Types:**
- **✓ Complete** (light green) - Step completed without pass/fail criteria
- **✓ Pass** (green) - Step passed inspection (all checkboxes checked or explicitly marked pass)
- **✗ Fail** (red) - Step failed inspection (incomplete checkboxes or explicitly marked fail)
- **Images**: All captured images with:
  - Camera source
  - Per-image notes
  - Annotation markers
  - Step context (Mode 2/3)

**Report Location:**
- Saved to `output/reports/`
- Filename: `{serial_number}_{timestamp}.pdf`

**Generating Reports:**
- **Mode 1**: Click "Generate Report" button
- **Mode 2/3**: Prompted after completing workflow

## Metadata Files

Each captured image/video has a companion JSON metadata file.

**Location:** Same directory as media file
**Filename:** `{filename}_metadata.json`

**Contents:**
- Filename
- Camera source
- Notes
- Timestamp
- Type (image/video)
- Annotation markers (positions, labels, angles)
- Serial number
- Description
- Step info (Mode 2/3)

**Use Case:** Raw data access for external processing or analysis

## File Organization

```
output/
├── captured_images/
│   └── {serial_number}/          # Images organized by serial number
│       ├── image1.jpg
│       ├── image1_metadata.json
│       ├── image2.jpg
│       └── image2_metadata.json
└── reports/                       # Generated PDF reports
    └── {serial_number}_{timestamp}.pdf

workflows/
├── qc_workflows/                  # Mode 2 workflows
│   └── *.json
└── maintenance_workflows/         # Mode 3 workflows
    └── *.json
```

## Workflow JSON Format

Workflows are stored as JSON files in the `workflows/` directory.

```json
{
  "name": "Workflow Name",
  "description": "Brief description",
  "steps": [
    {
      "title": "Step Title",
      "instructions": "Detailed instructions...",
      "reference_image": "/path/to/image.jpg",
      "require_photo": true,
      "require_annotations": false
    }
  ]
}
```

## Camera Support

- **Webcams**: Standard USB webcams
- **Borescopes**: USB borescope cameras
- **Multi-camera**: Automatic detection and selection
- **DirectShow**: Windows-optimized for fast initialization

**Camera Discovery:**
- Automatically detects cameras on startup
- Select from dropdown in application
- Fast initialization (< 1 second)

## Optional Features

### QR Code Scanning

Automatically scans QR codes from camera feed (if zbar library installed).

**Installation:**
- Linux: `sudo apt-get install libzbar0`
- Windows: Not available in standard repos

**Behavior:**
- Runs in background when camera active
- Automatically populates serial number field
- Multiple scans append with underscore separator

## Keyboard Shortcuts

- **Esc**: Close current dialog
- **Enter**: Confirm dialog (when focused)

## Tips and Best Practices

1. **Serial Numbers**: Use consistent format for easy organization
2. **Descriptions**: Be specific about the purpose of work
3. **Annotations**: Reference markers in notes for clarity
4. **Workflows**: Start with simple workflows and add complexity as needed
5. **Reference Images**: Use clear, high-quality reference images
6. **Step Instructions**: Write clear, concise instructions
7. **Reports**: Generate reports immediately after completing work

## Troubleshooting

**No cameras found:**
- Check camera is connected
- Try different USB port
- Restart application
- Check camera permissions

**Camera feed not showing:**
- Select different camera from dropdown
- Check camera is not in use by another application

**Workflow editor password:**
- Default password: `admin`
- Can be changed in `gui/workflow_selection.py`

**Report generation fails:**
- Check output directory exists and is writable
- Ensure at least one image captured
- Check disk space

**Markers not appearing on saved images:**
- Ensure markers are placed before capturing
- Check markers are visible in preview

## System Requirements

- **Python**: 3.7+ (3.13+ recommended)
- **Operating System**: Windows, Linux, macOS
- **Camera**: USB webcam or borescope
- **Display**: 1024x768 minimum resolution
- **Storage**: Varies based on image/video capture

## Dependencies

- PyQt5: GUI framework
- OpenCV: Camera capture and image processing
- Pillow: Image manipulation
- reportlab: PDF generation
- pyzbar: QR code scanning (optional)
- numpy: Array operations

## Project Structure

```
camera_qc_app/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── camera/                          # Camera abstraction layer
│   ├── camera_interface.py         # Base camera interface
│   ├── opencv_camera.py            # OpenCV implementation
│   └── camera_manager.py           # Camera discovery
├── gui/                             # GUI modules
│   ├── mode_selection.py           # Mode selection screen
│   ├── mode1_capture.py            # Mode 1 interface
│   ├── workflow_selection.py       # Workflow selection
│   ├── workflow_execution.py       # Step-by-step execution
│   ├── workflow_editor.py          # Workflow editor
│   └── annotatable_preview.py      # Camera preview with annotations
├── workflows/                       # Workflow definitions
│   ├── qc_workflows/               # QC workflows (JSON)
│   └── maintenance_workflows/      # Maintenance workflows (JSON)
├── reports/                         # PDF report generator
│   └── pdf_generator.py
└── output/                          # Generated files
    ├── captured_images/
    └── reports/
```

## Version History

- **v1.0**: Initial release with Mode 1
- **v2.0**: Added annotation system
- **v3.0**: Added Mode 2 and Mode 3 with workflows
- **v4.0**: Added workflow editor

## License

Internal use only - Emtech

## Support

For issues or questions, contact the development team.
