# PDF Report Generation

This module generates professional PDF reports from captured images and workflow data.

## Features

- **Session Information**: Serial number, description, timestamp, mode/workflow name
- **Checklist Results**: Optional pass/fail checklist items (for QC/maintenance workflows)
- **Image Gallery**: All captured images with captions and timestamps
- **Professional Layout**: Clean, organized format with proper spacing and styling

## Usage

### Simple Report (Mode 1)

```python
from reports import create_simple_report

# Generate report with captured images
report_path = create_simple_report(
    serial_number="PART-12345",
    description="General inspection",
    images=["path/to/image1.jpg", "path/to/image2.jpg"]
)
```

### Advanced Report (Mode 2/3)

```python
from reports import PDFReportGenerator

# Create checklist data
checklist = [
    {"name": "Visual inspection passed", "passed": True},
    {"name": "Dimensions within tolerance", "passed": True},
    {"name": "Surface finish acceptable", "passed": False}
]

# Generate report with workflow and checklist
generator = PDFReportGenerator()
report_path = generator.generate_report(
    serial_number="PART-12345",
    description="QC inspection",
    images=["path/to/image1.jpg"],
    mode_name="QC Workflow",
    workflow_name="Component Inspection v1.0",
    checklist_data=checklist
)
```

## Report Contents

### Header
- Title: "Camera QC Report"
- Professional styling with custom fonts

### Session Information Table
- Serial Number
- Description
- Mode/Workflow name
- Date and time

### Checklist Results (Optional)
- Table showing each checklist item
- Pass/Fail status with visual indicators (✓/✗)
- Alternating row colors for readability

### Image Gallery
- Each image with caption showing filename
- Images scaled to fit page width (6 inches)
- Automatic page breaks every 2 images
- Maintains aspect ratio

## Output

Reports are saved to `output/reports/` with filename format:
```
{serial_number}_{timestamp}.pdf
```

Example: `PART-12345_20260211_143022.pdf`

## Testing

Run the test suite to verify PDF generation:

```bash
python3 test_pdf_generation.py
```

This will:
1. Create test images
2. Generate sample reports (simple, advanced, empty)
3. Verify all reports are created successfully
4. Save test reports to `output/reports/`

## Integration with Mode 1

The "Generate Report" button in Mode 1 automatically:
1. Collects all captured images from the session
2. Uses the serial number and description from mode selection
3. Generates a PDF report
4. Shows success/error message with report location

## Future Enhancements

- Add workflow step details for Mode 2/3
- Include reference image comparisons
- Add measurement data tables
- Support for video thumbnails
- Digital signatures
- Custom branding/logos
