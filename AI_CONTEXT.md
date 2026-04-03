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
- Track work by serial number and technician name with QR code scanning support

## Technology Stack
- **GUI Framework**: PyQt5 (Python 3.7 compatible)
- **Camera**: OpenCV (webcam and USB borescope only - NO Basler/pypylon)
- **QR Scanning**: pyzbar (optional — camera-based scanning requires native ZBar library; gracefully disabled if unavailable)
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
- **camera_config_manager.py** - Camera settings profiles (Logitech, Microsoft, borescope, generic) and per-camera persistence
- Uses OpenCV VideoCapture for all camera access
- Camera discovery probes up to `max_camera_index` indices (default 8, configurable in User Preferences) with early exit after 4 consecutive failures for fast startup
- Each camera is closed immediately after probe to avoid holding USB resources that block discovery of remaining cameras
- Discovered cameras are cached in `MainWindow.cached_cameras` and shared across mode switches to avoid re-discovery
- Async camera discovery with `CameraDiscoveryThread` and `GearSpinnerWidget` loading animation

#### GUI (`gui/`)
- **mode_selection.py** - Initial screen for mode selection, job info entry, and `SerialScanDialog` for barcode-based serial number input
- **mode1_capture.py** - General capture interface with annotations
- **preferences_dialog.py** - Tabbed user preferences dialog (General, Appearance, Paths, Security)
- **workflow_selection.py** - Workflow selection screen for Mode 2/3 with search/filter
- **workflow_execution.py** - Step-by-step workflow execution with split-screen view
- **workflow_editor.py** - Password-protected workflow editor with unsaved changes protection
- **annotatable_preview.py** - Camera preview widget with annotation system
- **mask_editor.py** - Overlay mask creation tool
- **camera_settings_dialog.py** - Camera settings UI (brightness, contrast, resolution, etc.)
- **capture_review_dialog.py** - Post-capture dialog for annotating images and adding notes before saving
- **review_captures_dialog.py** - Dialog for reviewing/editing captured images and videos
- **overlay_comparison_dialog.py** - Side-by-side overlay comparison view
- **video_comparison_dialog.py** - Side-by-side video comparison view
- **comparison_dialog.py** - Full-size reference image view
- **overlay_renderer.py** - Shared overlay/marker rendering functions
- **video_decoder.py** - Threaded OpenCV video decoder (`VideoDecoderThread`)
- **checkbox_widgets.py** - Interactive inspection checkbox widgets (`InteractiveReferenceImage`, `CombinedReferenceImage`)
- **workflow_progress.py** - Progress save/load/clear functions
- **workflow_report.py** - Report generation and display helpers

#### Annotation System
- Rotatable arrow markers with sequential labels (A, B, C...)
- Variable arrow length (Shift+Scroll to adjust, max 300px)
- Left-click to add, drag to move, scroll to rotate, right-click to remove
- Markers saved with images and embedded in videos
- Uses relative coordinates for resolution independence

#### QR Code Scanner (`qr_scanner.py`)
- Camera-based barcode scanning using pyzbar (optional — gracefully disabled if native ZBar library missing)
- Runs passively in background thread when camera is active
- Automatically detects and reads QR codes
- Appends scanned data to serial number field (or sets it if empty)
- Works across all modes without user intervention
- Uses broad `except Exception` to handle missing DLLs (e.g., libiconv.dll, libzbar-64.dll on Windows)

#### USB Barcode Scanner (`usb_barcode_scanner.py`)
- Supports USB handheld barcode scanners in HID keyboard emulation mode
- No native libraries required — works on all platforms
- Intercepts rapid keyboard input to distinguish scanner from human typing
- Independent of pyzbar — works even when camera-based scanning is unavailable

#### Workflow System (`workflows/`)
- JSON-based workflow definitions
- `qc_workflows/` - Quality control process definitions
- `maintenance_workflows/` - Maintenance procedure definitions
- Each step can specify:
  - Instructions and reference images
  - Reference video (mp4, avi, mov, mkv, wmv, webm) with playback controls
  - Transparent PNG overlays with transform controls
  - Inspection checkboxes (bright amber/yellow)
  - Photo/annotation/pass-fail requirements
  - Step validation before proceeding

#### Reference Video System
- Steps can include a `reference_video` field alongside `reference_image`
- Video player replaces reference image display when a step has a video
- Playback controls: play/pause, restart, scrub slider, time display
- Uses `VideoDecoderThread` (QThread) for smooth background decoding via OpenCV
- Thread reads frames sequentially and emits QImages via signal at correct FPS
- Supports play/pause/seek commands via thread-safe methods
- Side-by-side comparison dialog: reference video on left, live camera on right
- Comparison dialog includes capture image, scan barcode, and record video buttons
- No audio playback support currently (OpenCV video-only)

#### PNG Overlay System
- Supports PNG images with alpha channel as camera overlays
- Transform controls: scale, position (X/Y offset), rotation, transparency
- Transforms persist across main view and comparison dialog
- Applied to live preview, captures, and video recordings
- "Hide Overlay Image" checkbox for temporary removal
- Auto-enables overlay mode for PNG images with alpha
- Overlay rendering function shared between views for consistency

#### Overlay Mask Editor (`gui/mask_editor.py`)
- Built-in tool for creating transparent PNG overlays from any captured image
- Accessible from workflow editor step dialog ("Create Overlay Mask from Image" button)
- Also accessible from Mode 1 via "🎭 Create Overlay Mask" button (capture current frame or browse existing images)
- MaskCanvas widget with zoom/pan, undo/redo (30 levels), brush cursor preview
- Tools: brush (adjustable 2-200px), rectangle, ellipse
- Two modes: Paint Transparency (default, paint areas to remove) and Paint Opacity (inverse, paint areas to keep)
- Left-click paints, right-click erases, scroll zooms, Ctrl+drag pans
- Checkerboard transparency preview with source image bleed-through (15% in paint transparency, 55% in paint opacity)
- Orange pixel-edge outline around opaque areas in paint opacity mode for clear brush visibility
- Saves PNG with alpha channel to resources/overlay_masks/
- After saving in workflow editor, offers to set mask as step reference image with overlay auto-enabled
- After saving in Mode 1, automatically sets as active overlay on live preview

#### Mode 1 Overlay System
- "Enable Overlay" checkbox with overlay filename display and clear button
- Overlay applied to live camera preview, captured images, and video recordings
- Overlay auto-activates when mask editor saves a new overlay
- Users can toggle overlay on/off at any time without losing the overlay path
- Overlay scales to fit camera frame using PNG alpha channel blending

#### Mode Selection Screen (`gui/mode_selection.py`)
- Required fields: serial number, technician name; optional: description
- Technician name auto-populated from saved preferences
- **SerialScanDialog**: Opens camera preview for scanning serial number via barcode/QR code
- **User Preferences button**: Opens `PreferencesDialog` for app settings (accent color, paths, password, etc.)
- **View Reports button**: Opens reports folder (custom or default) in system file explorer
- **Check for Updates button**: Runs `git fetch`/`git log` to check for and apply updates
- **Resume Incomplete Workflow button**: Lists saved progress files with delete option
- **Camera Settings button**: Opens `CameraSettingsDialog` for camera configuration

#### Review Captures (`gui/review_captures_dialog.py`)
- Dialog for reviewing all captured images and videos during a session
- Thumbnail list with full-size preview
- Edit per-image notes after capture
- Delete unwanted captures
- Shows step context for Mode 2/3 captures

#### Workflow Editor
- Password-protected (default: "admin", changeable in User Preferences → Security)
- Create, edit, delete workflows
- Add/edit/delete/reorder steps
- Place inspection checkboxes on reference images
- Reference video support (mp4, avi, mov, mkv, wmv, webm) per step
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

#### Theme System (`theme_manager.py`)
- `ThemeManager` class with light and dark mode stylesheets
- Toggle via "🌙 Dark Mode" / "☀️ Light Mode" button in top bar of `MainWindow`
- Accent color loaded from user preferences on startup (default: Emtech green #77C25E)
- `refresh_accent()` re-reads preferences and regenerates stylesheet
- Dark mode preference persisted to `settings/user_preferences.json` on toggle
- Applied globally to all widgets and dialogs

#### User Preferences (`preferences_manager.py`)
- Singleton `PreferencesManager` with JSON config at `settings/user_preferences.json`
- Settings: technician_name, default_camera_index, report_format, dark_mode, accent_color, default_marker_color, reports_output_dir, captured_images_dir, editor_password_hash, log_retention_days, max_camera_index, instructions_zoom
- `get_reports_dir()` / `get_captured_images_dir()` return custom or default paths
- `check_editor_password()` / `set_editor_password()` use SHA-256 hashing
- `get_accent_colors()` derives hover/pressed variants from base accent color
- Preferences dialog (`gui/preferences_dialog.py`) with tabs: General, Appearance, Paths, Security
- Technician name auto-populated on startup and saved when starting a session

#### Audit Logger (`audit_logger.py`)
- `AuditLogger` class writes hash-chained JSONL files to `output/audit/`
- Each entry includes SHA-256 of previous entry for tamper detection (genesis hash: 64 zeros)
- Events: session_start, session_end, image_capture, recording_start/stop, barcode_scan, step_complete, step_result, checkbox_changed, report_generated, progress_saved
- One audit file per session: `audit_{serial}_{timestamp}.jsonl`
- `verify_audit_file(path)` function validates the hash chain
- Wired into `main.py` (session lifecycle), `mode1_capture.py`, and `workflow_execution.py`

#### Logging (`logger_config.py`)
- Daily log files in `logs/` directory (auto-created)
- Filename format: `camera_qc_YYYYMMDD.log`
- Logs to both file and console
- Third-party loggers (PIL, matplotlib) set to WARNING to reduce noise
- All modules use `get_logger(name)` for module-specific loggers
- Log retention period configurable via user preferences (default: 30 days)

#### Global Exception Hook
- `main.py` installs `sys.excepthook` to catch unhandled exceptions
- Logs full tracebacks to prevent silent crashes
- Ensures errors are captured in log files for troubleshooting

#### Keyboard Shortcuts
- Space: Capture image (Mode 1, Mode 2/3, comparison dialogs)
- R: Toggle video recording
- B: Scan barcode/QR code
- All buttons use `Qt.NoFocus` policy to prevent Space from activating focused buttons
- Capture widgets use `Qt.StrongFocus` to receive key events

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
│   └── {serial_number}/     # Images organized by serial number (path customizable in preferences)
├── reports/                  # Generated PDF/DOCX reports (path customizable in preferences)
├── audit/                    # Session audit trail files (.jsonl, hash-chained)
└── progress/                 # Workflow progress files (auto-cleanup configurable days)
```

## Serial Number & Technician Handling
- **Required** - Both serial number and technician name must be entered before starting
- Serial number can be manually entered at startup
- Serial number can be scanned via the "Scan Serial QR/Barcode" button on the mode selection screen (opens `SerialScanDialog` with camera preview)
- Can also be scanned by USB handheld barcode scanner on the mode selection screen
- Multiple QR scans append to existing serial number with underscore separator
- Used for organizing output files and in report generation
- Technician name is included in reports and progress files

## Current Implementation Status

### ✅ Fully Implemented
- All three operating modes (Mode 1, 2, 3)
- Mode selection screen with required serial number and technician name
- Serial number scanning via camera (SerialScanDialog) or USB handheld scanner
- Dark/light mode theme toggle
- Camera discovery and management (OpenCV only)
- Multi-camera support (auto-discovery with async loading spinner)
- Camera settings dialog with profiles and per-camera persistence
- Passive QR code scanning across all modes (optional, graceful degradation)
- Annotation system with variable-length rotatable arrows and color picker
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
- Workflow import/export (zip packages with reference images and videos, and direct JSON)
- Progress save/resume functionality
- Progress file management (delete selected, auto-cleanup)
- Review captures dialog (edit notes, delete captures)
- Post-capture review dialog (annotate and add notes before saving)
- PDF and DOCX report generation
- Procedure summary tables with status indicators
- View Reports button (opens reports folder in file explorer)
- Check for Updates button (git-based, with dubious ownership detection and autostash)
- Keyboard shortcuts (Space/R/B) across all capture views
- Resizable instruction text in workflow execution (Ctrl+/-, persisted)
- Comprehensive logging to daily log files
- Global exception hook for crash prevention
- File organization by serial number
- User preferences system (technician name, accent color, output paths, editor password, log retention)
- Hash-chained audit trail for session actions
- Workflow search/filter on selection screen

## Important Design Decisions

### Camera Support
- **ONLY OpenCV cameras** - No Basler/pypylon support
- Supports standard USB webcams and borescope cameras
- Camera discovery probes up to `max_camera_index` indices (default 8, configurable in preferences) with early exit after 4 consecutive failures
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
- Customizable marker color via color picker button (default red)

### Video Recording
- MP4 container with H264 codec for compatibility
- Annotations rendered as overlay during recording
- Recording indicator with elapsed timer in UI
- Videos saved in progress and included in final reports

### Workflow Execution
- Split-screen layout: instructions/reference on left, live camera on right
- Step validation before allowing progression
- Automatic step failure if inspection checkboxes incomplete
- Progress auto-saved after each step completion, image capture, and barcode scan
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
- Shared rendering functions in `gui/overlay_renderer.py`
- Color picker in Mode 1 (`mode1_capture.py`) and Mode 2/3 (`workflow_execution.py`)

## Common Pitfall Warnings
- ⚠️ Do NOT add pypylon or Basler camera support
- ⚠️ Serial number and technician name are REQUIRED - validated before starting any mode
- ⚠️ QR scanner must run in separate thread (don't block UI)
- ⚠️ Always stop QR scanner thread in cleanup/closeEvent
- ⚠️ Camera indices may not be sequential - test each index
- ⚠️ Use relative coordinates for annotations (resolution independence)
- ⚠️ Always validate step requirements before allowing progression
- ⚠️ Clean up video writers properly to avoid corrupted files
- ⚠️ Workflow editor password stored as SHA-256 hash in preferences (default: "admin", change via User Preferences → Security)

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

## Recent Enhancements

### 2026-04-03: Update Button Fixes
- **Dubious Ownership Handling**: Detect git "dubious ownership" error and show user the exact `safe.directory` command to fix it, instead of misleading "not a git repo" message
- **Autostash on Pull**: Use `git pull --autostash` so local changes (e.g. edited workflows) are automatically preserved during updates

### 2026-04-01 – 2026-04-02: Stability & Hardening
- **Atomic File Writes**: Progress files and preferences written to `.tmp` then `os.replace()` to prevent corruption from crashes or power loss
- **Auto-Save on Capture**: Workflow progress saved after every image capture and barcode scan, not just step transitions
- **Resilient Cleanup**: Each resource (timer, video writer, QR scanner, camera) cleaned up independently with its own try/except/finally
- **Camera Discovery Fix**: Close each camera immediately after probe to avoid USB bandwidth contention; increase consecutive failure threshold from 2 to 4 for non-sequential indices
- **Orphaned Camera Cleanup**: If camera.open() succeeds but subsequent setup fails, camera is properly closed

### 2026-03-26: UX Polish & Post-Capture Review
- **Post-Capture Review Dialog**: `capture_review_dialog.py` — dialog appears after each capture for annotating and adding notes before saving
- **Resizable Instruction Text**: +/- buttons and Ctrl+/Ctrl- shortcuts to adjust instruction text size during workflow execution; zoom level persisted in preferences (`instructions_zoom`)
- **Background PDF Generation**: Instruction PDF generation runs in background thread to prevent UI freeze
- **Configurable Camera Discovery**: `max_camera_index` preference supports 4+ cameras with early exit on consecutive failures
- **Output Path Fallback Warning**: User warned when custom output paths (e.g. network share) are unavailable and defaults are used
- **Reference Videos in Export/Import**: Workflow export bundles reference videos alongside images; import warns on missing videos in JSON imports

### 2026-03-24: User Preferences, Audit Trail & Organization
- **User Preferences System**: `preferences_manager.py` with JSON config at `settings/user_preferences.json`
- **Preferences Dialog**: Tabbed dialog (General, Appearance, Paths, Security) accessible from mode selection screen
- **Technician Name Persistence**: Auto-populated from saved preferences on startup
- **Custom Accent Color**: User-selectable accent color with live theme refresh
- **Dark Mode Persistence**: Theme choice saved and restored across sessions
- **Custom Output Paths**: Configurable reports and captured images directories
- **Editor Password Management**: SHA-256 hashed password changeable via preferences (replaces hardcoded "admin")
- **Configurable Log Retention**: Days to keep log files adjustable in preferences
- **Default Camera/Marker Color**: Saved per-user preferences
- **Report Format Preference**: Choose PDF only, DOCX only, or both
- **Hash-Chained Audit Trail**: `audit_logger.py` writes JSONL files with SHA-256 chain to `output/audit/`
- **Audit Events**: session start/end, image captures, recordings, barcode scans, step completions, pass/fail, checkbox changes, report generation
- **Workflow Search/Filter**: Text filter box on workflow selection screen for quick lookup
- **File Organization**: Moved development docs to `docs/`, test files to `tests/`

### 2026-03-17: Polish, Hardening & Import Improvements
- **Keyboard Shortcuts**: Space (capture), R (record), B (barcode scan) across all capture views
- **Focus Management**: NoFocus on buttons, StrongFocus on capture widgets to prevent Space activating Back button
- **Shortcut Labels**: Keyboard shortcuts shown in button text (e.g., "📸 Capture Image (Space)")
- **Direct JSON Import**: Workflow editor can now import `.json` files directly, not just `.zip` packages
- **PDF Fix**: Long step titles wrap in table cells instead of clipping
- **pyzbar DLL Crash Fix**: Graceful handling of missing native ZBar libraries
- **Global Exception Hook**: `sys.excepthook` installed to catch and log unhandled exceptions

### 2026-03-16: Major Refactor & Stability
- **Module Extraction**: Extracted 5 modules from `workflow_execution.py` (3383→1936 lines): `overlay_comparison_dialog.py`, `overlay_renderer.py`, `video_comparison_dialog.py`, `workflow_progress.py`, `workflow_report.py`
- **Overlay Transform Persistence**: Per-step overlay transforms saved to workflow JSON and persist across sessions
- **Async Camera Discovery**: Background thread with gear spinner animation during camera detection
- **Ctrl+Z Crash Fix**: Fixed undo crash in mask editor
- **Camera Disconnect Handling**: Detect and recover from camera disconnects during capture

### 2026-03-12: Camera Reliability & Code Quality
- **Silent Camera Failure Prevention**: Detect double-open, handle disconnects gracefully
- **Module Extraction**: Extracted `checkbox_widgets.py`, `comparison_dialog.py`, `video_decoder.py` from `workflow_execution.py`
- **Bare Except Cleanup**: Replaced bare `except:` clauses with specific exception handling

### 2026-03-11: Reference Video & USB Barcode Scanner
- **USB HID Barcode Scanner**: Global keystroke interceptor for handheld scanners (`usb_barcode_scanner.py`)
- **Reference Videos in Workflows**: Steps can include reference videos with built-in player
- **VideoDecoderThread**: Background OpenCV decoder for smooth playback without codec dependencies
- **Video Comparison Dialog**: Side-by-side reference video + live camera with capture/record
- **Video Player Iteration**: Went through QMediaPlayer → OpenCV threaded decoder for cross-platform reliability

### 2026-03-10: Reference Video Support & Mode 1 Overlay Tools
- **Reference Videos in Workflows**: Steps can now include reference videos (mp4, avi, mov, etc.) alongside reference images
- **Video Player**: Built-in player with play/pause, restart, scrub slider, and time display in workflow step view
- **VideoDecoderThread**: Background QThread decodes frames via OpenCV for smooth real-time playback without codec dependencies
- **Video Comparison Dialog**: Side-by-side view with reference video on left and live camera on right, with full capture/scan/record capabilities
- **Mode 1 Overlay Mask Editor**: "🎭 Create Overlay Mask" button with option to capture current camera frame or browse existing images
- **Mode 1 Overlay Toggle**: "Enable Overlay" checkbox applies overlay to live preview, captures, and video recordings
- **Mask Editor UX**: Checkerboard shows source image bleed-through (15% paint transparency, 55% paint opacity mode)
- **Paint Opacity Edge Outline**: Orange pixel-edge border around opaque areas using morphological dilation (no shape-closing artifacts)
- **Camera Settings Fixes**: Gray webcam fix, simplified discovery, default 1080p profiles

### 2026-03-09: Overlay Mask Editor
- **Built-in Mask Editor**: Create transparent PNG overlays from any captured image without external tools
- **Drawing Tools**: Brush (2-200px), rectangle, and ellipse for defining transparent/opaque regions
- **Two Paint Modes**: Paint Transparency (remove areas) and Paint Opacity/Inverse (keep areas)
- **Full Editing Features**: Undo/redo (30 levels), zoom/pan, checkerboard preview, reset mask
- **Workflow Integration**: Accessible from workflow editor step dialog, auto-sets as reference image

### 2026-03-06: Step Navigation & Photo Requirements
- **Configurable Photo Count**: Workflow steps can require multiple photos (1-50) via spinbox in editor
- **Previous Step Navigation**: Previous Step button and clickable breadcrumb steps fully functional
- **Breadcrumb Jump**: Click any visited step to jump directly, all visited steps remain clickable
- **Progress Save on Navigation**: Auto-saves on any step transition (forward, backward, breadcrumb)
- **Back-to-Menu Dialog**: Choice between saving progress for resume or generating partial report
- **Mode 1 Button Styling**: Aligned button colors/layout with Mode 2/3 (orange scan, red record)

### 2026-03-03: PNG Overlay System
- **Transparent PNG Overlays**: Upload PNG images with alpha channel as overlays on camera feed
- **Transform Controls**: Scale (50-200%), position (±100px X/Y), rotation (±180°), transparency (0-100%)
- **Persistent Transforms**: Settings saved and synchronized between main view and comparison dialog
- **Overlay Rendering**: Applied to live preview, captures, and video recordings
- **Hide Overlay Toggle**: Checkbox to temporarily remove overlay from view and captures
- **Auto-detection**: Automatically detects PNG alpha channel and enables overlay mode
- **Button Labels**: Dynamic button text based on image type (Overlay Settings vs Reference Comparison)
- **Camera Settings**: Fixed grayscale/color issues, added Restart Camera button, improved settings dialog

### 2026-02-26: Workflow Management
- Unsaved changes protection in workflow editor
- Variable arrow length (Shift+Scroll, 50-300px max)
- MP4 video recording with annotation overlays
- Resume incomplete workflow feature
- Progress file management with auto-cleanup
- Checkbox state syncing in fullsize reference view
- Improved UI/UX (button reordering, color coding)
- Comprehensive logging and error handling
