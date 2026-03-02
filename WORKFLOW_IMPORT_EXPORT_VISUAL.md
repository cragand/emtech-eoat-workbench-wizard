# Workflow Import/Export - Visual Guide

## Export Process Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Editor                          │
│                                                             │
│  ┌──────────────────┐                                      │
│  │  Workflow List   │                                      │
│  │                  │                                      │
│  │  • Inspection A  │ ◄── User selects workflow           │
│  │  • Inspection B  │                                      │
│  │  • Maintenance C │                                      │
│  └──────────────────┘                                      │
│                                                             │
│  [Export Workflow] ◄── User clicks export button           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              System Collects Workflow Data                  │
│                                                             │
│  Workflow JSON:                                             │
│  • Name: "Inspection A"                                     │
│  • Description: "..."                                       │
│  • Steps: [...]                                             │
│                                                             │
│  Reference Images:                                          │
│  • /home/user/images/step1.jpg                             │
│  • /mnt/shared/refs/step2.png                              │
│  • C:\Users\tech\Desktop\step3.jpg                         │
│                                                             │
│  (Images can be ANYWHERE on filesystem)                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Create ZIP Package                         │
│                                                             │
│  inspection_a_20260302_193000.zip                          │
│  ├── workflow.json                                          │
│  ├── manifest.json                                          │
│  └── images/                                                │
│      ├── step1.jpg                                          │
│      ├── step2.png                                          │
│      └── step3.jpg                                          │
│                                                             │
│  All images copied into package!                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Save Dialog                               │
│                                                             │
│  Save to: [/home/user/Downloads/inspection_a...zip]        │
│                                                             │
│  [Cancel]  [Save]  ◄── User chooses location               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                    ✓ Export Complete!
```

## Import Process Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Editor                          │
│                                                             │
│  [Import Workflow] ◄── User clicks import button           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   File Selection Dialog                     │
│                                                             │
│  Select file: [inspection_a_20260302_193000.zip]           │
│                                                             │
│  [Cancel]  [Open]  ◄── User selects zip file               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Validate ZIP Package                       │
│                                                             │
│  ✓ Contains workflow.json                                   │
│  ✓ Contains manifest.json                                   │
│  ✓ Valid JSON structure                                     │
│  ✓ Images directory present                                 │
│                                                             │
│  Check for conflicts:                                       │
│  • Name already exists? → Ask user                          │
│  • Mode mismatch? → Warn user                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                Extract and Process                          │
│                                                             │
│  1. Extract images to resources/ directory:                 │
│     • step1.jpg → resources/qc_reference_images/step1.jpg  │
│     • step2.png → resources/qc_reference_images/step2.png  │
│     • step3.jpg → resources/qc_reference_images/step3.jpg  │
│                                                             │
│  2. Update workflow JSON paths:                             │
│     OLD: /home/user/images/step1.jpg                       │
│     NEW: resources/qc_reference_images/step1.jpg           │
│                                                             │
│  3. Save workflow to workflows/ directory                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Success Dialog                            │
│                                                             │
│  Workflow imported successfully!                            │
│                                                             │
│  Name: Inspection A                                         │
│  Images imported: 3                                         │
│  Steps: 5                                                   │
│                                                             │
│  [OK]                                                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Workflow List Refreshed                        │
│                                                             │
│  ┌──────────────────┐                                      │
│  │  Workflow List   │                                      │
│  │                  │                                      │
│  │  • Inspection A  │ ◄── Newly imported workflow          │
│  │  • Inspection B  │                                      │
│  │  • Maintenance C │                                      │
│  └──────────────────┘                                      │
│                                                             │
│  Ready to use immediately!                                  │
└─────────────────────────────────────────────────────────────┘
```

## File Structure Comparison

### Before Export (Original Machine)

```
camera_qc_app/
├── workflows/
│   └── qc_workflows/
│       └── inspection_a.json  ◄── References images below
│
└── (Images scattered across filesystem)
    ├── /home/user/images/step1.jpg
    ├── /mnt/shared/refs/step2.png
    └── /tmp/step3.jpg
```

### Exported Package

```
inspection_a_20260302_193000.zip
├── workflow.json           ◄── Workflow definition
├── manifest.json          ◄── Metadata
└── images/                ◄── All images bundled together
    ├── step1.jpg
    ├── step2.png
    └── step3.jpg
```

### After Import (New Machine)

```
camera_qc_app/
├── workflows/
│   └── qc_workflows/
│       └── inspection_a.json  ◄── Paths updated to point below
│
└── resources/
    └── qc_reference_images/   ◄── Images extracted here
        ├── step1.jpg
        ├── step2.png
        └── step3.jpg
```

## Path Transformation Example

### Original Workflow (Machine A)
```json
{
  "name": "Inspection A",
  "steps": [
    {
      "title": "Step 1",
      "reference_image": "/home/user/images/step1.jpg"
    },
    {
      "title": "Step 2",
      "reference_image": "C:\\Users\\tech\\Desktop\\step2.png"
    }
  ]
}
```

### In Export Package
```json
{
  "name": "Inspection A",
  "steps": [
    {
      "title": "Step 1",
      "reference_image": "/home/user/images/step1.jpg"
    },
    {
      "title": "Step 2",
      "reference_image": "C:\\Users\\tech\\Desktop\\step2.png"
    }
  ]
}
```
(Original paths preserved, but images are in `images/` directory)

### After Import (Machine B)
```json
{
  "name": "Inspection A",
  "steps": [
    {
      "title": "Step 1",
      "reference_image": "resources/qc_reference_images/step1.jpg"
    },
    {
      "title": "Step 2",
      "reference_image": "resources/qc_reference_images/step2.png"
    }
  ]
}
```
(Paths automatically updated to new locations)

## Conflict Resolution

### Name Conflict

```
┌─────────────────────────────────────────────────────────────┐
│                  Workflow Exists                            │
│                                                             │
│  A workflow named "Inspection A" already exists.            │
│                                                             │
│  Overwrite it?                                              │
│                                                             │
│  [Yes - Overwrite]  [No - Keep Both]                        │
└─────────────────────────────────────────────────────────────┘
                │                        │
                │                        │
        [Yes]   │                        │   [No]
                ▼                        ▼
    Replace existing workflow    Rename to "Inspection A (20260302_193000)"
```

### Mode Mismatch

```
┌─────────────────────────────────────────────────────────────┐
│                    Mode Mismatch                            │
│                                                             │
│  This workflow was exported from a different mode.          │
│                                                             │
│  Current mode: QC                                           │
│  Workflow mode: Maintenance                                 │
│                                                             │
│  Import anyway?                                             │
│                                                             │
│  [Yes]  [No]                                                │
└─────────────────────────────────────────────────────────────┘
```

## Button States

### Export Button
```
Disabled (gray):  No workflow selected
Enabled (blue):   Workflow selected
```

### Import Button
```
Always enabled (purple): Ready to import anytime
```

## Use Cases

### 1. Sharing Between Colleagues
```
Technician A                    Technician B
    │                               │
    ├─ Create workflow              │
    ├─ Add reference images         │
    ├─ Export to USB drive          │
    │                               │
    └─────── USB drive ─────────────┤
                                    │
                                    ├─ Import from USB
                                    ├─ Workflow ready!
                                    └─ All images work!
```

### 2. Backup and Restore
```
Before Changes              After Changes
    │                           │
    ├─ Export workflow          ├─ Made mistakes?
    │  (backup)                 │
    │                           ├─ Import backup
    └─ Make changes             └─ Restored!
```

### 3. Multi-Site Deployment
```
    Headquarters
         │
         ├─ Create standard workflow
         ├─ Export package
         │
         ├────────┬────────┬────────┐
         │        │        │        │
      Site A   Site B   Site C   Site D
         │        │        │        │
         └────────┴────────┴────────┘
              All import same workflow
              Standardized process!
```
