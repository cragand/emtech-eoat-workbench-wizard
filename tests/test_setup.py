#!/usr/bin/env python3
"""Test script to verify camera_qc_app dependencies and camera availability."""

import sys

def test_imports():
    """Test all required imports."""
    print("Testing imports...")
    try:
        import cv2
        print("  ✓ opencv-python")
    except ImportError as e:
        print(f"  ✗ opencv-python: {e}")
        return False
    
    try:
        from PyQt5.QtWidgets import QApplication
        print("  ✓ PyQt5")
    except ImportError as e:
        print(f"  ✗ PyQt5: {e}")
        return False
    
    try:
        from pyzbar import pyzbar
        print("  ✓ pyzbar")
    except ImportError as e:
        print(f"  ✗ pyzbar: {e}")
        print("    Install ZBar: sudo apt-get install libzbar0")
        return False
    
    try:
        from PIL import Image
        print("  ✓ Pillow")
    except ImportError as e:
        print(f"  ✗ Pillow: {e}")
        return False
    
    try:
        from reportlab.pdfgen import canvas
        print("  ✓ reportlab")
    except ImportError as e:
        print(f"  ✗ reportlab: {e}")
        return False
    
    return True

def test_cameras():
    """Test camera availability."""
    print("\nTesting cameras...")
    import cv2
    
    found_cameras = []
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                found_cameras.append((i, w, h))
                print(f"  ✓ Camera {i}: {w}x{h}")
            cap.release()
        else:
            break
    
    if not found_cameras:
        print("  ✗ No cameras found")
        print("    Check: ls /dev/video*")
        return False
    
    return True

def test_qr_decode():
    """Test QR code decoding capability."""
    print("\nTesting QR decoder...")
    try:
        from pyzbar import pyzbar
        import numpy as np
        from PIL import Image, ImageDraw
        
        # Create a simple test (won't actually decode, just test API)
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        decoded = pyzbar.decode(test_img)
        print("  ✓ QR decoder functional")
        return True
    except Exception as e:
        print(f"  ✗ QR decoder error: {e}")
        return False

def test_file_structure():
    """Test required directories exist."""
    print("\nChecking file structure...")
    import os
    
    required_dirs = [
        "camera",
        "gui",
        "workflows",
        "output",
        "resources"
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ {dir_name}/ missing")
            all_exist = False
    
    if os.path.isfile("main.py"):
        print("  ✓ main.py")
    else:
        print("  ✗ main.py missing")
        all_exist = False
    
    return all_exist

def main():
    """Run all tests."""
    print("=" * 50)
    print("Camera QC App - System Test")
    print("=" * 50)
    
    results = {
        "Imports": test_imports(),
        "Cameras": test_cameras(),
        "QR Decoder": test_qr_decode(),
        "File Structure": test_file_structure()
    }
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:20s} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("\n✓ All tests passed! Ready to run: python main.py")
        return 0
    else:
        print("\n✗ Some tests failed. Fix issues before running main.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())
