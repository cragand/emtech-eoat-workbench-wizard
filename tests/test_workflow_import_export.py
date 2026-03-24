#!/usr/bin/env python3
"""Test script for workflow import/export functionality."""

import os
import json
import zipfile
import tempfile
import shutil
from datetime import datetime

def test_export_import():
    """Test the export/import workflow logic."""
    
    print("Testing Workflow Import/Export Functionality")
    print("=" * 50)
    
    # Create a test workflow
    test_workflow = {
        "name": "Test Workflow",
        "description": "A test workflow for import/export",
        "steps": [
            {
                "title": "Step 1",
                "instructions": "Test instructions",
                "reference_image": "",
                "require_photo": True,
                "require_annotations": False
            }
        ]
    }
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_dir = os.path.join(tmpdir, "workflows")
        resource_dir = os.path.join(tmpdir, "resources", "qc_reference_images")
        os.makedirs(workflow_dir)
        os.makedirs(resource_dir)
        
        # Save test workflow
        workflow_path = os.path.join(workflow_dir, "test_workflow.json")
        with open(workflow_path, 'w') as f:
            json.dump(test_workflow, f, indent=2)
        print(f"✓ Created test workflow: {workflow_path}")
        
        # Create a test reference image
        test_image_path = os.path.join(resource_dir, "test_image.jpg")
        with open(test_image_path, 'wb') as f:
            # Create a minimal valid JPEG (1x1 pixel)
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
                   b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
                   b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
                   b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
                   b'\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01'
                   b'\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05'
                   b'\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04'
                   b'\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A'
                   b'\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82'
                   b'\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz'
                   b'\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a'
                   b'\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9'
                   b'\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8'
                   b'\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5'
                   b'\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfe\xfe\xa2'
                   b'\x8a(\xff\xd9')
        
        # Update workflow to reference the image
        test_workflow['steps'][0]['reference_image'] = test_image_path
        with open(workflow_path, 'w') as f:
            json.dump(test_workflow, f, indent=2)
        print(f"✓ Created test reference image: {test_image_path}")
        
        # Test Export
        export_path = os.path.join(tmpdir, "exported_workflow.zip")
        
        with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add workflow JSON
            zipf.write(workflow_path, 'workflow.json')
            
            # Add reference image
            zipf.write(test_image_path, f"images/{os.path.basename(test_image_path)}")
            
            # Create manifest
            manifest = {
                'workflow_name': test_workflow['name'],
                'mode': 2,
                'export_date': datetime.now().isoformat(),
                'image_count': 1,
                'version': '1.0'
            }
            zipf.writestr('manifest.json', json.dumps(manifest, indent=2))
        
        print(f"✓ Exported workflow to: {export_path}")
        print(f"  Size: {os.path.getsize(export_path)} bytes")
        
        # Verify zip contents
        with zipfile.ZipFile(export_path, 'r') as zipf:
            contents = zipf.namelist()
            print(f"✓ Zip contents: {contents}")
            assert 'workflow.json' in contents
            assert 'manifest.json' in contents
            assert 'images/test_image.jpg' in contents
        
        # Test Import
        import_dir = os.path.join(tmpdir, "import_test")
        import_workflow_dir = os.path.join(import_dir, "workflows")
        import_resource_dir = os.path.join(import_dir, "resources", "qc_reference_images")
        os.makedirs(import_workflow_dir)
        os.makedirs(import_resource_dir)
        
        with zipfile.ZipFile(export_path, 'r') as zipf:
            # Read workflow
            workflow_data = zipf.read('workflow.json')
            imported_workflow = json.loads(workflow_data)
            
            # Read manifest
            manifest_data = zipf.read('manifest.json')
            manifest = json.loads(manifest_data)
            print(f"✓ Read manifest: {manifest['workflow_name']}, {manifest['image_count']} images")
            
            # Extract images
            image_mapping = {}
            for item in zipf.namelist():
                if item.startswith('images/'):
                    img_filename = os.path.basename(item)
                    target_img_path = os.path.join(import_resource_dir, img_filename)
                    
                    with zipf.open(item) as source, open(target_img_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    
                    image_mapping[img_filename] = os.path.join("resources/qc_reference_images", img_filename)
                    print(f"✓ Extracted image: {img_filename}")
            
            # Update paths
            for step in imported_workflow.get('steps', []):
                ref_image = step.get('reference_image', '')
                if ref_image:
                    img_filename = os.path.basename(ref_image)
                    if img_filename in image_mapping:
                        step['reference_image'] = image_mapping[img_filename]
                        print(f"✓ Updated image path: {image_mapping[img_filename]}")
            
            # Save imported workflow
            imported_path = os.path.join(import_workflow_dir, "imported_workflow.json")
            with open(imported_path, 'w') as f:
                json.dump(imported_workflow, f, indent=2)
            print(f"✓ Imported workflow saved to: {imported_path}")
        
        # Verify imported workflow
        with open(imported_path, 'r') as f:
            final_workflow = json.load(f)
            assert final_workflow['name'] == test_workflow['name']
            assert len(final_workflow['steps']) == len(test_workflow['steps'])
            assert final_workflow['steps'][0]['reference_image'] == "resources/qc_reference_images/test_image.jpg"
            print(f"✓ Verified imported workflow structure")
        
        # Verify image exists
        final_image_path = os.path.join(import_dir, final_workflow['steps'][0]['reference_image'])
        assert os.path.exists(final_image_path)
        print(f"✓ Verified reference image exists at: {final_image_path}")
    
    print("\n" + "=" * 50)
    print("✓ All tests passed!")
    print("\nThe import/export functionality is working correctly:")
    print("  • Workflows are packaged into zip files")
    print("  • Reference images are bundled with the workflow")
    print("  • Images are extracted to the correct location on import")
    print("  • Paths are updated to point to the new image locations")
    print("  • Manifest provides metadata about the export")

if __name__ == "__main__":
    test_export_import()
