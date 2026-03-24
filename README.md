# Emtech EoAT Workbench Wizard

Quality control and maintenance application with guided workflows, camera integration, and annotation system.

## Quick Start (Windows)

**Easy Method - Double-click to run:**
1. Unzip the application folder
2. Double-click `runEEWW.bat`
3. First run will automatically set up the environment (takes 1-2 minutes)
4. Subsequent runs launch immediately

> **Note:** The quick start method does not support automatic updates. See [Full Installation](#full-installation-with-automatic-updates) below for the recommended setup.

## Quick Start (Linux)

**Easy Method - Run script:**
1. Unzip the application folder
2. Make the script executable (first time only):
   ```bash
   chmod +x runEEWW.sh
   ```
3. Run the script:
   ```bash
   ./runEEWW.sh
   ```
4. First run will automatically set up the environment (takes 1-2 minutes)
5. Subsequent runs launch immediately

> **Note:** The quick start method does not support automatic updates. See [Full Installation](#full-installation-with-automatic-updates) below for the recommended setup.

## Full Installation (with Automatic Updates)

The recommended installation uses Git to clone the repository, which enables one-click updates via `updateEEWW.bat`.

### Prerequisites

- **Python 3.7+** (3.13+ recommended) — [Download](https://www.python.org/downloads/)
- **Git** — [Download for Windows](https://git-scm.com/download/win) (use default options during install)

### Windows

1. Open a Command Prompt and navigate to where you want the app:
   ```cmd
   cd C:\Users\%USERNAME%\Downloads
   ```

2. Clone the repository:
   ```cmd
   git clone https://github.com/cragand/emtech-eoat-workbench-wizard.git
   ```

3. Navigate into the folder and run:
   ```cmd
   cd emtech-eoat-workbench-wizard
   runEEWW.bat
   ```

4. To check for and apply updates, double-click `updateEEWW.bat` at any time. It will:
   - Show your current version
   - Check for available updates
   - List what changed
   - Ask for confirmation before applying
   - Automatically update dependencies if needed

### Linux

1. Clone the repository:
   ```bash
   cd ~/Downloads
   git clone https://github.com/cragand/emtech-eoat-workbench-wizard.git
   ```

2. Navigate into the folder and run:
   ```bash
   cd emtech-eoat-workbench-wizard
   chmod +x runEEWW.sh updateEEWW.sh
   ./runEEWW.sh
   ```

3. To check for and apply updates:
   ```bash
   ./updateEEWW.sh
   ```

### Migrating from Zip to Git

If you originally received EEWW as a zip file and want to switch to the git-based setup for automatic updates:

1. Clone the repository to a new folder (see steps above)
2. Copy your existing `workflows/` and `output/` folders into the new location
3. Use the new folder going forward — your workflows and reports will be preserved

## Manual Setup

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

## Application Features

### Mode Selection Screen

The main screen where you configure each session before starting.

**Required Fields:**
- **Serial Number**: Identifies the unit being worked on. Can be typed manually or scanned via the "Scan Serial QR/Barcode" button, which opens a camera preview for barcode scanning.
- **Technician Name**: Name of the person performing the work.
- **Description**: Purpose of the work session (optional but recommended).

**Bottom Bar Buttons:**
- **⚙️ Camera Settings**: Open camera configuration dialog (brightness, contrast, resolution, etc.)
- **🔧 User Preferences**: Open preferences dialog (see [User Preferences](#user-preferences) below)
- **📁 View Reports**: Open the reports folder in your system file explorer
- **📂 Resume Incomplete Workflow**: Resume a previously saved workflow session
- **🔄 Check for Updates**: Check for and apply updates via git (requires git-based installation)

### User Preferences

Accessible from the mode selection screen via the "🔧 User Preferences" button. Settings are saved to `settings/user_preferences.json` and persist across sessions.

**General Tab:**
- **Technician Name**: Remembered between sessions and auto-populated on startup
- **Default Camera Index**: Pre-select a specific camera on startup
- **Report Format**: Choose PDF only, DOCX only, or both (default: both)
- **Log Retention**: Number of days to keep log files (default: 30)

**Appearance Tab:**
- **Theme**: Toggle dark/light mode (persisted across sessions)
- **Accent Color**: Customize the application accent color (default: Emtech green #77C25E)
- **Default Marker Color**: Set the default annotation marker color (default: red)

**Paths Tab:**
- **Reports Folder**: Custom output directory for generated reports (default: `output/reports/`)
- **Captured Images Folder**: Custom directory for captured images (default: `output/captured_images/`)

**Security Tab:**
- **Change Editor Password**: Update the workflow editor password (default: `admin`)

### Dark/Light Mode

Toggle between light and dark themes using the "🌙 Dark Mode" / "☀️ Light Mode" button in the top-right corner. The theme applies to all screens and dialogs. Theme preference is saved in User Preferences and persists across sessions. The accent color can be customized in User Preferences (default: Emtech brand green #77C25E).

### Camera Settings

Accessible from the mode selection screen or within any capture view via the ⚙️ button.

- Adjust brightness, contrast, saturation, sharpness, exposure, focus, and white balance
- Built-in camera profiles for Logitech, Microsoft, borescope, and generic webcams
- Factory reset to restore default settings
- Restart camera to apply changes
- Settings are saved per camera and persist across sessions

### Review Captures

Click "📋 Review Captures" during any session to open a dialog showing all captured images and videos.

- Thumbnail list with preview
- Edit per-image notes after capture
- View full-size images
- Delete unwanted captures

## Application Modes

### Mode 1: General Image Capture

Free-form capture mode for quick documentation.

**Features:**
- Live camera preview
- Multi-camera support (auto-detection)
- Image and video capture
- Annotation markers (rotatable arrows with labels)
- Per-image notes
- Optional barcode/QR code scanning
- Overlay mask creation and live overlay toggle
- Generate PDF and DOCX reports

**How to use:**
1. Enter serial number, technician name, and description
2. Select Mode 1 and click Start
3. Choose camera from dropdown
4. Add annotations by clicking on preview
   - Left-click: Add marker (A, B, C...)
   - Drag: Move marker
   - Scroll wheel: Rotate marker
   - Shift+Scroll: Adjust arrow length (50-300px)
   - Right-click: Remove marker
5. Add notes for each image (optional)
6. Scan barcodes/QR codes when needed (button enabled when detected)
7. Click "Capture Image" to save
8. Click "Generate Report" when done

**Overlay Masks in Mode 1:**
- Click "🎭 Create Overlay Mask" to open the mask editor
- Choose "📷 Capture Current Frame" to use the live camera image, or "📂 Browse for Image..." to select an existing file
- Paint transparent/opaque regions and save the overlay PNG
- The overlay automatically activates on the live preview after saving
- Use the "Enable Overlay" checkbox to toggle the overlay on/off
- Overlay is applied to captured images and video recordings when enabled
- Click "✕" to remove the overlay entirely

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
1. Enter serial number, technician name, and description
2. Select Mode 2 and click Start
3. Choose a workflow from the list (use the search/filter box to narrow results)
4. Click "Start Workflow"
5. Follow instructions for each step
6. Capture required photos with annotations
7. Click "Next Step" to proceed (validates requirements)
8. Click "Finish Workflow" to complete
9. Generate report with checklist

**Step Requirements:**
- Some steps require photo capture before proceeding
- Some steps require annotations on photos
- Some steps require barcode/QR code scanning
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
- **Import/Export workflows** - Share workflows with all reference images packaged together

**Import/Export:**
- **Export**: Package workflow and all reference images into a single `.zip` file
- **Import**: Extract workflow from `.zip` and automatically set up images
- Reference images are copied from any location and bundled with the workflow
- Paths are automatically updated on import
- See [WORKFLOW_IMPORT_EXPORT.md](docs/WORKFLOW_IMPORT_EXPORT.md) for detailed documentation

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
   - Require barcode scan (checkbox)
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
- **Reference Video**: Optional video (mp4, avi, mov, mkv, wmv, webm) to display alongside camera with playback controls
- **Transparent Overlay**: Check to use PNG image as overlay on camera feed (requires PNG with alpha channel)
- **Place Checkboxes**: Add inspection points on reference image (bright amber/yellow boxes)
- **Require Photo**: User must capture at least one photo
- **Require Annotations**: User must add markers to photos
- **Require Barcode Scan**: User must scan at least one barcode/QR code
- **Require Pass/Fail**: User must explicitly mark step as pass or fail

**PNG Overlay Feature:**
- Upload PNG images with transparency to overlay on live camera feed
- Overlay appears on main workflow screen and comparison view
- Transform controls: scale (50-200%), position (±100px X/Y), rotation (±180°), transparency (0-100%)
- Transforms persist across views and are saved with captures/recordings
- "Hide Overlay Image" checkbox temporarily removes overlay from view and captures
- Ideal for alignment guides, templates, or measurement overlays

**Creating Overlay Masks (Built-in Mask Editor):**
- Open the Workflow Editor, edit any step, and click "🎭 Create Overlay Mask from Image"
- Load any captured image (JPG, PNG, BMP, etc.) as the starting point
- Use painting tools to define which areas become transparent (camera shows through) or opaque (overlay remains visible)
- **Tools available:**
  - Brush: Freehand painting with adjustable size (2-200px)
  - Rectangle: Click and drag to define rectangular transparent/opaque regions
  - Ellipse: Click and drag to define elliptical transparent/opaque regions
- **Two paint modes:**
  - Paint Transparency (default): Start with full image, paint areas to make transparent
  - Paint Opacity (inverse): Start transparent, paint only the areas you want to keep
- Left-click paints, right-click erases, scroll wheel zooms, Ctrl+drag pans
- Undo/Redo support (Ctrl+Z / Ctrl+Y, up to 30 levels)
- Checkerboard preview shows transparent vs opaque areas
- Saves as PNG with alpha channel to `resources/overlay_masks/`
- After saving, the editor offers to set the mask as the step's reference image with overlay mode auto-enabled

**Inspection Checkboxes:**
- Click on reference image to place checkboxes at inspection points
- Left-click: Add checkbox
- Right-click: Remove checkbox
- Checkboxes appear as bright amber/yellow squares
- During workflow execution, user clicks checkboxes to mark inspection complete
- Step automatically fails if not all checkboxes are checked

**Reference Image Comparison:**
- Click "🔍 Reference Comparison View" button to open side-by-side comparison
- Split view: Reference image with checkboxes | Live camera feed
- Overlay mode: Blend reference and camera with adjustable transparency
- Capture images and record videos directly from comparison view
- All annotations and markers are preserved

**PNG Overlay Mode:**
- For steps with PNG overlay images, button shows "⚙️ Overlay Settings/Zoom View"
- Automatically opens in overlay mode with transform controls
- **Transform Controls:**
  - Scale: 50-200% (resize overlay)
  - Position: ±100px X/Y offset (move overlay)
  - Rotation: ±180° (rotate overlay)
  - Transparency: 0-100% (blend with camera feed)
- Transforms apply to main view and all captures/recordings
- Reset button restores default transform values
- "Hide Overlay Image" checkbox on main view temporarily removes overlay

**Reference Video Playback:**
- Steps can include a reference video that displays in place of the reference image
- Built-in video player with play/pause, restart, scrub slider, and time display
- Videos play at correct speed using a background decoder thread (OpenCV-based, no extra codec installs needed)
- Supports mp4, avi, mov, mkv, wmv, and webm formats
- Click "🔍 Reference Comparison View" for side-by-side: reference video on left, live camera on right
- Comparison view includes capture image, scan barcode, and record video buttons
- Note: Audio playback is not currently supported

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
- Colored arrows with white label circles (default red, customizable via color picker)
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
- **Session Information**: Serial number, technician name, description, date/time
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
      "reference_video": "/path/to/video.mp4",
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

### Barcode/QR Code Scanning

Scan barcodes and QR codes during any workflow step or general capture (if pyzbar library installed).

**Two scanning methods:**
- **Camera-based scanning**: Uses pyzbar to detect barcodes in the camera feed (requires native ZBar library)
- **USB handheld scanner**: Works automatically with any USB barcode scanner in HID keyboard mode (no extra software needed)

**Camera-based scanning installation:**
- Linux: `sudo apt-get install libzbar0`
- Windows: Download and install ZBar from https://sourceforge.net/projects/zbar/files/zbar/0.10/zbar-0.10-setup.exe/download

> **Note:** If camera-based scanning is not available, the app will still work — the scan button will be disabled but USB handheld scanners function independently.

**Supported Formats:**
- QR Code
- EAN/UPC barcodes
- Code 128, Code 39
- DataMatrix, PDF417
- And many others supported by pyzbar

**How to Use:**
1. Point camera at barcode/QR code
2. "Scan Barcode/QR" button becomes enabled when code is detected
3. Click button to capture scan
4. Dialog shows barcode type, data, and scan count
5. Current camera frame is automatically captured
6. Scan data appears in generated reports

**Behavior:**
- Button is always visible but grayed out when no barcode detected
- Runs passively in background when camera is active
- Does NOT auto-populate serial number field
- Scans are optional unless required by workflow step
- Multiple scans can be captured per step/session
- All scans appear in report summary table and with captured images

**In Reports:**
- Session info shows total scan count
- Dedicated "Barcode Scans" section with table (Type, Data, Timestamp)
- Each scanned image shows barcode type and data
- Available in both PDF and DOCX formats

## Keyboard Shortcuts

**All capture views (Mode 1, Mode 2/3, Comparison dialogs):**
- **Space**: Capture image
- **R**: Toggle video recording
- **B**: Scan barcode/QR code

**General:**
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
- Can be changed in User Preferences → Security tab

**Report generation fails:**
- Check output directory exists and is writable
- Ensure at least one image captured
- Check disk space

**Markers not appearing on saved images:**
- Ensure markers are placed before capturing
- Check markers are visible in preview

**Application logs:**
- Log files are written to the `logs/` directory (created automatically)
- Daily log files named `camera_qc_YYYYMMDD.log`
- Contains detailed error information for troubleshooting
- Log retention period is configurable in User Preferences (default: 30 days)

**Audit trail:**
- Each session writes a hash-chained `.jsonl` file to `output/audit/`
- Every entry includes a SHA-256 hash of the previous entry for tamper detection
- Events logged: session start/end, image captures, video recordings, barcode scans, step completions, pass/fail results, checkbox changes, report generation
- Audit files are named `audit_{serial}_{timestamp}.jsonl`

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
- python-docx: DOCX generation
- pyzbar: Camera-based barcode/QR scanning (optional — requires native ZBar library; see Optional Features)
- numpy: Array operations

> **Note:** USB handheld barcode scanners work without pyzbar — they use HID keyboard emulation handled by `usb_barcode_scanner.py`.

## Project Structure

```
camera_qc_app/
├── main.py                          # Application entry point
├── theme_manager.py                 # Light/dark mode theme system
├── preferences_manager.py           # User preferences (JSON config)
├── audit_logger.py                  # Hash-chained session audit trail
├── logger_config.py                 # Logging configuration
├── qr_scanner.py                    # Camera-based QR/barcode scanner thread
├── usb_barcode_scanner.py           # USB HID barcode scanner interceptor
├── requirements.txt                 # Python dependencies
├── runEEWW.bat / runEEWW.sh         # Quick-start launcher scripts
├── updateEEWW.bat / updateEEWW.sh   # Update scripts (git-based)
├── camera/                          # Camera abstraction layer
│   ├── camera_interface.py         # Base camera interface
│   ├── opencv_camera.py            # OpenCV implementation
│   ├── camera_manager.py           # Camera discovery
│   └── camera_config_manager.py    # Camera settings profiles and persistence
├── gui/                             # GUI modules
│   ├── mode_selection.py           # Mode selection screen + serial scan dialog
│   ├── mode1_capture.py            # Mode 1 interface
│   ├── preferences_dialog.py       # User preferences dialog
│   ├── workflow_selection.py       # Workflow selection for Mode 2/3 (with search/filter)
│   ├── workflow_execution.py       # Step-by-step workflow execution
│   ├── workflow_editor.py          # Workflow editor with import/export
│   ├── annotatable_preview.py      # Camera preview with annotation system
│   ├── mask_editor.py              # Overlay mask creation tool
│   ├── camera_settings_dialog.py   # Camera settings UI
│   ├── review_captures_dialog.py   # Review/edit captured images dialog
│   ├── overlay_comparison_dialog.py # Side-by-side overlay comparison view
│   ├── video_comparison_dialog.py  # Side-by-side video comparison view
│   ├── comparison_dialog.py        # Full-size reference image view
│   ├── overlay_renderer.py         # Shared overlay/marker rendering functions
│   ├── video_decoder.py            # Threaded OpenCV video decoder
│   ├── checkbox_widgets.py         # Interactive inspection checkbox widgets
│   ├── workflow_progress.py        # Progress save/load/clear functions
│   └── workflow_report.py          # Report generation and display
├── workflows/                       # Workflow definitions
│   ├── workflow_loader.py          # Workflow JSON loader
│   ├── qc_workflows/               # QC workflows (JSON)
│   └── maintenance_workflows/      # Maintenance workflows (JSON)
├── reports/                         # Report generators
│   ├── report_generator.py         # Factory for PDF/DOCX generation
│   ├── pdf_generator.py            # PDF report generation (reportlab)
│   ├── docx_generator.py           # DOCX report generation (python-docx)
│   └── workflow_instructions_generator.py  # Printable workflow instruction PDFs
├── resources/                       # Static resources
│   ├── overlay_masks/              # Saved overlay mask PNGs
│   ├── qc_reference_images/        # QC workflow reference images
│   └── maintenance_reference_images/ # Maintenance reference images
├── settings/                        # Saved camera settings and user preferences (JSON)
├── docs/                            # Development documentation
├── tests/                           # Test scripts
├── logs/                            # Application log files (daily)
└── output/                          # Generated files
    ├── captured_images/             # Images organized by serial number
    ├── reports/                     # Generated PDF/DOCX reports
    ├── audit/                       # Session audit trail files (.jsonl)
    └── progress/                    # Workflow progress files
```

## Version History

- **v1.0**: Initial release with Mode 1
- **v2.0**: Added annotation system
- **v3.0**: Added Mode 2 and Mode 3 with workflows
- **v4.0**: Added workflow editor
- **v5.0**: User preferences system, audit trail, workflow search/filter, customizable accent color and output paths

## License

Internal use only - Emtech

## Support

For issues or questions, contact the development team.
