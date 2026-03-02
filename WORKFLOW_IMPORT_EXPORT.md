# Workflow Import/Export Feature

## Overview

The workflow editor now includes import/export functionality that allows you to easily share workflows between installations, including all reference images.

## Features

### Export Workflow
- Packages workflow JSON and all reference images into a single `.zip` file
- Includes metadata (workflow name, mode, export date, image count)
- Reference images are copied from their current location (can be anywhere on filesystem)
- Exported files are portable and self-contained

### Import Workflow
- Extracts workflow and images from `.zip` package
- Automatically copies images to the correct `resources/` directory
- Updates image paths in the workflow to point to new locations
- Validates package structure and checks for conflicts
- Handles mode compatibility warnings
- Offers options when workflow name already exists

## How to Use

### Exporting a Workflow

1. Open the workflow editor (Mode 2 or Mode 3 → "Edit Workflows" → password: `admin`)
2. Select the workflow you want to export from the list
3. Click the **"Export Workflow"** button (blue)
4. Choose where to save the `.zip` file
5. The workflow and all its reference images will be packaged together

**Export includes:**
- Workflow JSON with all steps and settings
- All reference images (from any location)
- Manifest file with metadata
- Inspection checkbox data

### Importing a Workflow

1. Open the workflow editor
2. Click the **"Import Workflow"** button (purple)
3. Select the `.zip` file to import
4. Review any warnings (mode mismatch, name conflicts)
5. The workflow will be imported and immediately available

**Import process:**
- Extracts workflow JSON
- Copies images to `resources/qc_reference_images/` or `resources/maintenance_reference_images/`
- Updates all image paths in the workflow
- Handles name conflicts (option to overwrite or rename)
- Validates package structure

## Package Structure

Exported `.zip` files contain:

```
workflow_package.zip
├── workflow.json           # Workflow definition
├── manifest.json          # Metadata (name, mode, date, image count)
└── images/                # Reference images
    ├── image1.jpg
    ├── image2.png
    └── ...
```

### Manifest Example

```json
{
  "workflow_name": "Camera Inspection",
  "mode": 2,
  "export_date": "2026-03-02T19:30:00.000000",
  "image_count": 3,
  "version": "1.0"
}
```

## Conflict Handling

### Name Conflicts
If a workflow with the same name already exists:
- **Overwrite**: Replace the existing workflow
- **Rename**: Append timestamp to create unique name (e.g., "Workflow_20260302_193000")

### Mode Mismatch
If importing a QC workflow into Maintenance mode (or vice versa):
- Warning dialog appears
- Option to import anyway or cancel
- Workflow will be placed in the current mode's directory

## Benefits

1. **Easy Sharing**: Share workflows with colleagues via email, USB, network drive
2. **Backup**: Export workflows for safekeeping
3. **Portability**: Reference images are bundled, no manual file copying needed
4. **Version Control**: Export before making changes to create restore points
5. **Multi-Site**: Standardize workflows across multiple installations
6. **No Manual Path Updates**: Image paths are automatically corrected on import

## Technical Details

### Image Path Handling

**On Export:**
- Reads reference images from their current location (anywhere on filesystem)
- Copies images into the zip package
- Original paths are preserved in the workflow JSON

**On Import:**
- Extracts images to appropriate `resources/` directory
- Updates workflow JSON to use new relative paths
- Format: `resources/qc_reference_images/image.jpg`

### Supported Image Formats
- PNG (.png)
- JPEG (.jpg, .jpeg)
- BMP (.bmp)

### File Naming
Exported files use format: `{workflow_name}_{timestamp}.zip`
- Example: `camera_inspection_20260302_193000.zip`

## Troubleshooting

**Export button is disabled:**
- Select a workflow from the list first

**Import fails with "Invalid workflow package":**
- Ensure the file is a valid workflow export (contains `workflow.json`)
- Don't manually modify the zip structure

**Images not showing after import:**
- Check that images were extracted to `resources/` directory
- Verify paths in workflow JSON are relative (not absolute)

**Mode mismatch warning:**
- Workflow was exported from different mode (QC vs Maintenance)
- You can still import, but verify it makes sense for your use case

## Best Practices

1. **Export before major edits**: Create a backup before making significant changes
2. **Use descriptive names**: Workflow names should be clear and unique
3. **Test imports**: After importing, open the workflow to verify images load correctly
4. **Organize exports**: Keep exported workflows in a dedicated folder for easy access
5. **Document changes**: Update workflow descriptions when making modifications

## Example Workflow

**Sharing a workflow with a colleague:**

1. You: Export workflow → Save to USB drive
2. Colleague: Copy zip file to their machine
3. Colleague: Open workflow editor → Import workflow
4. Colleague: Workflow is ready to use with all images

**No manual steps needed for:**
- Copying reference images
- Updating image paths
- Creating directory structure
- Configuring file locations
