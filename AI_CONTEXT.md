# AI Context: Camera QC Application

## Project Overview
This is a Python-based quality control and maintenance application designed for manufacturing/lab environments. It provides guided workflows with camera integration for documentation and reporting.

## Core Purpose
- Perform systematic quality control checks on manufactured components
- Guide technicians through maintenance/repair procedures
- Capture images/video during processes for documentation
- Generate PDF reports with captured media and workflow results
- Track work by serial number (optional) with QR code scanning support

## Technology Stack
- **GUI Framework**: PyQt5 (Python 3.7 compatible)
- **Camera**: OpenCV (webcam and USB borescope only - NO Basler/pypylon)
- **QR Scanning**: pyzbar (passive background scanning, optional)
- **Reporting**: reportlab 3.6.x (PDF generation)
- **Image Processing**: Pillow, OpenCV

## Application Architecture

### Three Operating Modes
1. **Mode 1: General Image Capture** - Free-form image/video capture with any camera
2. **Mode 2: QC Process** - Guided quality control with checklists (NOT YET IMPLEMENTED)
3. **Mode 3: Maintenance/Repair** - Guided maintenance procedures (NOT YET IMPLEMENTED)

### Key Components

#### Camera System (`camera/`)
- **camera_interface.py** - Abstract base class for camera implementations
- **opencv_camera.py** - OpenCV camera implementation (webcam/borescope)
- **camera_manager.py** - Discovers and manages available cameras
- Uses OpenCV VideoCapture for all camera access

#### GUI (`gui/`)
- **mode_selection.py** - Initial screen for mode selection and job info entry
- **mode1_capture.py** - General capture interface (IMPLEMENTED)
- **mode2_qc.py** - QC workflow interface (NOT YET IMPLEMENTED)
- **mode3_maintenance.py** - Maintenance workflow interface (NOT YET IMPLEMENTED)

#### QR Code Scanner (`qr_scanner.py`)
- Runs passively in background thread when camera is active
- Automatically detects and reads QR codes
- Appends scanned data to serial number field (or sets it if empty)
- Works across all modes without user intervention

#### Reports (`reports/`)
- **pdf_generator.py** - PDF report generation with reportlab
- **PDFReportGenerator** class - Full-featured report generation
- **create_simple_report()** - Convenience function for quick reports
- Supports session info, images, checklists, and workflow data
- Professional layout with tables, styling, and automatic pagination
- JSON-based workflow definitions
- `qc_workflows/` - Quality control process definitions
- `maintenance_workflows/` - Maintenance procedure definitions
- Each step can specify camera type, reference images, checklists, photo requirements

#### Output Structure
```
output/
├── captured_images/
│   └── {serial_number}/     # Images organized by serial number
└── reports/                  # Generated PDF reports
```

## Serial Number Handling
- **Optional** - User can proceed without entering a serial number
- Can be manually entered at startup
- Can be automatically populated by QR code scanner
- Multiple QR scans append to existing serial number with underscore separator
- Used for organizing output files and in report generation
- Defaults to "unknown" for file organization if not provided

## Current Implementation Status

### ✅ Completed
- Mode selection screen with optional serial number
- Mode 1: General image capture with live preview
- Camera discovery and management (OpenCV only)
- Passive QR code scanning across all modes (optional, graceful degradation)
- Basic file organization by serial number
- Multi-camera support (auto-discovery)
- PDF report generation with images and session info
- Report generation integrated into Mode 1

### ⏳ Not Yet Implemented
- Mode 2: QC workflow execution
- Mode 3: Maintenance workflow execution
- Workflow JSON parsing and execution
- Reference image display
- Checklist tracking (UI integration)

## Important Design Decisions

### Camera Support
- **ONLY OpenCV cameras** - No Basler/pypylon support
- Supports standard USB webcams and borescope cameras
- Camera discovery checks indices 0-4 for available devices

### QR Scanner Behavior
- Runs in separate thread to avoid blocking UI
- Scans every 100ms when camera is active
- Only emits signal when NEW QR code detected (prevents duplicates)
- Automatically stops when camera disconnects or mode closes

### File Naming Convention
- Format: `{serial_number}_{timestamp}.{ext}`
- Timestamp: `YYYYMMDD_HHMMSS`
- If no serial number: uses "unknown" as prefix

## Development Guidelines

### Adding New Modes
1. Create new screen class inheriting from QWidget
2. Accept `serial_number` and `description` in `__init__`
3. Import and initialize `QRScannerThread` when camera connects
4. Connect `qr_detected` signal to handler that updates serial number
5. Stop QR scanner in `closeEvent`
6. Update `main.py` to instantiate new mode

### Workflow Integration
- Workflows are JSON files defining step-by-step procedures
- Each step can specify camera type, reference images, requirements
- Parser should load JSON and create UI dynamically
- Track completion status and collect photos per step

### Report Generation
- Should include: serial number, description, timestamp, workflow name
- Embed captured images with step context
- Include checklist results if applicable
- Save to `output/reports/{serial_number}_{timestamp}.pdf`

## Common Pitfall Warnings
- ⚠️ Do NOT add pypylon or Basler camera support
- ⚠️ Serial number is OPTIONAL - never require it
- ⚠️ QR scanner must run in separate thread (don't block UI)
- ⚠️ Always stop QR scanner thread in cleanup/closeEvent
- ⚠️ Camera indices may not be sequential - test each index

## Testing Considerations
- Test with no cameras connected (graceful degradation)
- Test with multiple cameras (selection should work)
- Test QR scanning with various QR code formats
- Test with and without serial numbers
- Verify file organization when serial number changes mid-session
