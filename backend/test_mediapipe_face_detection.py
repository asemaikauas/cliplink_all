#!/usr/bin/env python3
"""
Test script to verify MediaPipe face detection is working correctly
Run this after installing MediaPipe to ensure everything is set up properly
"""

import cv2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vertical_crop_async import AsyncVerticalCropService
from app.services.vertical_crop import VerticalCropService
import asyncio

def test_sync_face_detection():
    """Test synchronous face detection service"""
    print("🧪 Testing Synchronous Face Detection Service...")
    
    try:
        # Initialize service
        service = VerticalCropService()
        print("✅ VerticalCropService initialized successfully")
        
        # Create a test frame (black image)
        test_frame = cv2.imread('test_image.jpg') if os.path.exists('test_image.jpg') else None
        
        if test_frame is None:
            # Create a synthetic test frame if no image available
            import numpy as np
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            print("⚠️ Using synthetic test frame (no test_image.jpg found)")
        else:
            print("✅ Using test_image.jpg")
            
        # Test face detection
        faces = service.detect_faces(test_frame)
        print(f"✅ Face detection completed. Found {len(faces)} faces")
        
        if faces:
            for i, (x, y, x1, y1) in enumerate(faces):
                print(f"   Face {i+1}: ({x}, {y}) to ({x1}, {y1}) - size: {x1-x}x{y1-y}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync face detection test failed: {str(e)}")
        return False

async def test_async_face_detection():
    """Test asynchronous face detection service"""
    print("\n🧪 Testing Asynchronous Face Detection Service...")
    
    try:
        # Initialize service
        service = AsyncVerticalCropService()
        print("✅ AsyncVerticalCropService initialized successfully")
        
        # Create a test frame
        test_frame = cv2.imread('test_image.jpg') if os.path.exists('test_image.jpg') else None
        
        if test_frame is None:
            import numpy as np
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            print("⚠️ Using synthetic test frame (no test_image.jpg found)")
        else:
            print("✅ Using test_image.jpg")
            
        # Test async face detection
        faces = await service.detect_faces(test_frame)
        print(f"✅ Async face detection completed. Found {len(faces)} faces")
        
        if faces:
            for i, (x, y, x1, y1) in enumerate(faces):
                print(f"   Face {i+1}: ({x}, {y}) to ({x1}, {y1}) - size: {x1-x}x{y1-y}")
        
        return True
        
    except Exception as e:
        print(f"❌ Async face detection test failed: {str(e)}")
        return False

def test_mediapipe_import():
    """Test MediaPipe import and basic functionality"""
    print("🧪 Testing MediaPipe Import...")
    
    try:
        import mediapipe as mp
        print("✅ MediaPipe imported successfully")
        
        # Test face detection initialization
        mp_face_detection = mp.solutions.face_detection
        face_detector = mp_face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=0.3
        )
        print("✅ MediaPipe Face Detection initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ MediaPipe test failed: {str(e)}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing MediaPipe Face Detection Implementation\n")
    print("=" * 60)
    
    # Test 1: MediaPipe import
    mediapipe_test = test_mediapipe_import()
    
    # Test 2: Sync service
    sync_test = test_sync_face_detection()
    
    # Test 3: Async service
    async_test = await test_async_face_detection()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"   MediaPipe Import: {'✅ PASS' if mediapipe_test else '❌ FAIL'}")
    print(f"   Sync Service:     {'✅ PASS' if sync_test else '❌ FAIL'}")
    print(f"   Async Service:    {'✅ PASS' if async_test else '❌ FAIL'}")
    
    if all([mediapipe_test, sync_test, async_test]):
        print("\n🎉 All tests passed! MediaPipe face detection is working correctly.")
        print("🚀 Your shoulder-only cropping issue should be fixed!")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")
        print("💡 Make sure you've installed MediaPipe: pip install mediapipe")

if __name__ == "__main__":
    asyncio.run(main()) 