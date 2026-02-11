#!/usr/bin/env python3
"""Test script for PDF report generation."""

import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reports import create_simple_report, PDFReportGenerator


def create_test_images(output_dir, count=3):
    """Create dummy test images."""
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []
    
    for i in range(count):
        # Create a simple test image
        img = Image.new('RGB', (640, 480), color=(73, 109, 137))
        draw = ImageDraw.Draw(img)
        
        # Add text
        text = f"Test Image {i+1}\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        draw.text((250, 220), text, fill=(255, 255, 255))
        
        # Save image
        filename = f"test_image_{i+1}.jpg"
        filepath = os.path.join(output_dir, filename)
        img.save(filepath)
        image_paths.append(filepath)
        print(f"Created: {filepath}")
    
    return image_paths


def test_simple_report():
    """Test simple report generation."""
    print("\n" + "="*50)
    print("Testing Simple Report Generation")
    print("="*50)
    
    # Create test images
    test_dir = "output/test_images"
    images = create_test_images(test_dir, count=3)
    
    # Generate report
    try:
        report_path = create_simple_report(
            serial_number="TEST-12345",
            description="Test report generation with sample images",
            images=images
        )
        print(f"\n✓ Report generated successfully!")
        print(f"  Location: {report_path}")
        print(f"  Images: {len(images)}")
        return True
    except Exception as e:
        print(f"\n✗ Report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_advanced_report():
    """Test advanced report with checklist."""
    print("\n" + "="*50)
    print("Testing Advanced Report with Checklist")
    print("="*50)
    
    # Create test images
    test_dir = "output/test_images"
    images = create_test_images(test_dir, count=2)
    
    # Create checklist data
    checklist = [
        {"name": "Visual inspection passed", "passed": True},
        {"name": "Dimensions within tolerance", "passed": True},
        {"name": "Surface finish acceptable", "passed": False},
        {"name": "No defects found", "passed": True}
    ]
    
    # Generate report with checklist
    try:
        generator = PDFReportGenerator()
        report_path = generator.generate_report(
            serial_number="TEST-67890",
            description="Advanced test with QC checklist",
            images=images,
            mode_name="QC Workflow",
            workflow_name="Component Inspection v1.0",
            checklist_data=checklist
        )
        print(f"\n✓ Advanced report generated successfully!")
        print(f"  Location: {report_path}")
        print(f"  Images: {len(images)}")
        print(f"  Checklist items: {len(checklist)}")
        return True
    except Exception as e:
        print(f"\n✗ Advanced report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_images_report():
    """Test report generation with no images."""
    print("\n" + "="*50)
    print("Testing Report with No Images")
    print("="*50)
    
    try:
        report_path = create_simple_report(
            serial_number="TEST-EMPTY",
            description="Test report with no images",
            images=[]
        )
        print(f"\n✓ Empty report generated successfully!")
        print(f"  Location: {report_path}")
        return True
    except Exception as e:
        print(f"\n✗ Empty report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*50)
    print("PDF Report Generator Test Suite")
    print("="*50)
    
    results = []
    
    # Test 1: Simple report
    results.append(("Simple Report", test_simple_report()))
    
    # Test 2: Advanced report with checklist
    results.append(("Advanced Report", test_advanced_report()))
    
    # Test 3: Report with no images
    results.append(("Empty Report", test_no_images_report()))
    
    # Summary
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:30} {status}")
    
    all_passed = all(result[1] for result in results)
    print("="*50)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
