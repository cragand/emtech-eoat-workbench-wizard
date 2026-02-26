# Workflow Editor - Unsaved Changes Protection

## Changes Made (2026-02-26)

Added unsaved changes tracking to prevent accidental data loss when editing workflows.

## New Behavior

The workflow editor now:
- Tracks when any changes are made to a workflow
- Prompts user before navigating away from unsaved changes
- Provides three options: Save, Discard, or Cancel

## Protected Actions

Users are now prompted when they have unsaved changes and attempt to:
1. Click on a different workflow in the list
2. Click "New Workflow" button
3. Click "Back" button

## Implementation Details

### New Instance Variables
- `has_unsaved_changes` - Boolean flag set when any edit is made
- `saved_state` - JSON snapshot of last saved state for comparison

### Change Detection
Changes are marked when:
- Workflow name is modified (textChanged signal)
- Description is modified (textChanged signal)
- Steps are added, edited, deleted, or reordered

### Prompt Dialog
When unsaved changes are detected:
- **Save**: Attempts to save the workflow, then proceeds with navigation
- **Discard**: Abandons changes and proceeds with navigation
- **Cancel**: Stays in current workflow editor

### State Management
- `saved_state` is updated after successful save
- `has_unsaved_changes` is reset after save or when loading a workflow
- State comparison uses JSON serialization for accuracy

## User Experience

Before: Users could lose hours of work by accidentally clicking elsewhere
After: Users are always prompted to save before losing work
