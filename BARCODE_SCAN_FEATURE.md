# Barcode/QR Scan Feature Implementation

## Overview
Added optional barcode/QR code scanning functionality to all three modes (Mode 1, 2, and 3) with report integration.

## Changes Made (2026-02-26)

### Core Scanner Updates

#### `qr_scanner.py`
- Renamed from QR-only to general barcode scanner
- Changed signal from `qr_detected(str)` to `barcode_detected(str, str)` - emits (type, data)
- Added `get_current_barcode()` method to check if barcode is currently detected
- Stores current detection state for button enable/disable logic
- Supports all pyzbar barcode types (QR, EAN, Code128, DataMatrix, etc.)

### Mode 1 (General Capture)

#### `gui/mode1_capture.py`
- Added "Scan Barcode/QR" button between Capture and Record buttons
- Button is half-width (150px max) to prioritize capture/record buttons
- Button enabled only when barcode is detected in camera view
- Removed auto-append to serial number field
- Added `barcode_scans` list to track all scans in session
- Added `scan_barcode()` method:
  - Captures current frame
  - Saves image with note "Barcode scan capture ([type]): [data]"
  - Shows dialog with barcode type, data, and scan count
  - Stores scan info: {type, data, timestamp}
- Added `update_scan_button_state()` timer callback (100ms) to enable/disable button
- Added `barcode_check_timer` cleanup in `cleanup_resources()`
- Updated `generate_report()` to pass `barcode_scans` parameter

### Mode 2/3 (Workflow Execution)

#### `gui/workflow_execution.py`
- Added "Scan Barcode/QR" button between Capture and Record buttons
- Button enabled only when barcode is detected
- Added `step_barcode_scans` list to track scans per step
- Added `scan_barcode()` method:
  - Captures frame with barcode info
  - Saves image with step context
  - Shows dialog with scan count for current step
  - Stores scan with step number
- Clears `step_barcode_scans` when moving to next step
- Added barcode scan requirement validation in `validate_step()`
- Collects all barcode scans from images for report generation
- Added `barcode_check_timer` cleanup in `cleanup_resources()`
- Scanner auto-starts when camera connects

### Workflow Editor

#### `gui/workflow_editor.py`
- Added "Require barcode scan" checkbox in Requirements section
- Checkbox appears between "Require annotations" and "Require pass/fail"
- Tooltip: "User must scan at least one barcode/QR code before proceeding"
- Stored in workflow JSON as `require_barcode_scan: true/false`
- Loaded and saved with other step requirements

### Report Generation

#### `reports/report_generator.py`
- Added `barcode_scans` parameter to `generate_reports()` function
- Passes barcode scans to both PDF and DOCX generators

#### `reports/pdf_generator.py`
- Added `barcode_scans` parameter to `generate_report()` method
- Added "Scan Info" row to session information table showing scan count
- Added "Barcode Scans" section with table:
  - Columns: #, Type, Data, Timestamp
  - Green header (#77C25E)
  - Alternating row backgrounds
- Added barcode scan info to individual image captions
- Shows as "Barcode Scans:" with bullet list of type and data

#### `reports/docx_generator.py`
- Added `barcode_scans` parameter to `generate_report()` method
- Added "Scan Info" row to session information table
- Added "Barcode Scans" section with table (4 columns)
- Added barcode scan info to individual image captions (both images and videos)
- Shows as bullet list under each image with scan data

## User Experience

### Scanning Workflow
1. User starts any mode with camera active
2. "Scan Barcode/QR" button is grayed out by default
3. When barcode enters camera view, button becomes enabled
4. User clicks button to capture scan
5. Dialog shows:
   - Barcode type (e.g., "QRCODE", "EAN13", "CODE128")
   - Barcode data
   - Scan count for current context (session for Mode 1, step for Mode 2/3)
6. Current frame is captured and saved with barcode note
7. Scan data is stored for report generation

### Report Output
- **Session Info Table**: Shows total scan count
- **Barcode Scans Section**: Detailed table of all scans with timestamps
- **Individual Images**: Each scan shows type and data with the captured image
- **Summary Table (Mode 2/3)**: Can include scan info per step

### Workflow Requirements (Mode 2/3)
- Workflow editor allows marking steps as requiring barcode scan
- Step validation prevents progression without required scan
- Warning dialog explains requirement if not met

## Technical Details

### Data Structures

**Barcode Scan Object:**
```python
{
    'type': 'QRCODE',  # Barcode type from pyzbar
    'data': 'ABC123',  # Decoded data
    'timestamp': '2026-02-26 19:30:00',
    'step': 1  # Only in Mode 2/3
}
```

**Image Data with Barcode:**
```python
{
    'path': '/path/to/image.jpg',
    'camera': 'Camera 0',
    'notes': 'Barcode scan capture (QRCODE): ABC123',
    'barcode_scans': [scan_object],
    'markers': [],
    'step': 1,  # Mode 2/3 only
    'step_title': 'Step Name'  # Mode 2/3 only
}
```

### Button Sizing
- Capture Image: Full width (default)
- Scan Barcode/QR: 150px max width
- Record Video: Full width (default)

### Timer Management
- `barcode_check_timer`: 100ms interval to update button state
- Checks `qr_scanner.get_current_barcode()` for detection
- Stopped in `cleanup_resources()` to prevent memory leaks

## Backward Compatibility
- Existing workflows without `require_barcode_scan` default to `False`
- Reports without barcode scans display normally (sections omitted)
- Old image data format (without `barcode_scans`) handled gracefully

## Testing Checklist
- [ ] Mode 1: Scan button appears and enables when barcode detected
- [ ] Mode 1: Scan captures image and shows dialog
- [ ] Mode 1: Multiple scans accumulate in session
- [ ] Mode 1: Report shows all scans in table and with images
- [ ] Mode 2/3: Scan button works during workflow execution
- [ ] Mode 2/3: Scans reset between steps
- [ ] Mode 2/3: Scan count shows per-step count in dialog
- [ ] Mode 2/3: Required scan validation prevents next step
- [ ] Workflow Editor: Require barcode scan checkbox saves/loads
- [ ] Reports: PDF shows barcode scans section and in image captions
- [ ] Reports: DOCX shows barcode scans section and in image captions
- [ ] Various barcode types detected (QR, EAN, Code128, etc.)
- [ ] Button grays out when no barcode in view
- [ ] Cleanup: No timer leaks when closing application

## Future Enhancements
- Filter by specific barcode types (e.g., only QR codes)
- Barcode data validation (regex patterns)
- Auto-scan mode (capture on detection without button click)
- Barcode history/duplicate detection
- Export barcode data to CSV
