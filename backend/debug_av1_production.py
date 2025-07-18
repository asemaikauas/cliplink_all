#!/usr/bin/env python3
"""
Debug script to check what's wrong with AV1 support in production
Run this in your Docker container to see what's missing
"""

import subprocess
import sys
import cv2
import os

def check_installed_packages():
    """Check what AV1 packages are actually installed"""
    print("🔍 Checking installed AV1 packages...")
    
    packages_to_check = ['libdav1d6', 'libaom3', 'ffmpeg']
    
    for package in packages_to_check:
        try:
            result = subprocess.run(['dpkg', '-l', package], capture_output=True, text=True)
            if result.returncode == 0 and package in result.stdout:
                print(f"✅ {package} is installed")
            else:
                print(f"❌ {package} is NOT installed")
        except Exception as e:
            print(f"❌ Error checking {package}: {e}")

def check_ffmpeg_av1_support():
    """Check FFmpeg AV1 codec support"""
    print("\n🔍 Checking FFmpeg AV1 support...")
    
    try:
        result = subprocess.run(['ffmpeg', '-codecs'], capture_output=True, text=True)
        
        av1_lines = [line for line in result.stdout.split('\n') if 'av1' in line.lower()]
        
        if av1_lines:
            print("✅ FFmpeg has AV1 codecs:")
            for line in av1_lines:
                print(f"   {line.strip()}")
        else:
            print("❌ FFmpeg has NO AV1 codecs")
            
        # Check specific decoders
        av1_decoders = [line for line in av1_lines if 'D' in line[:10]]
        if av1_decoders:
            print(f"✅ Found {len(av1_decoders)} AV1 decoders")
        else:
            print("❌ NO AV1 decoders found")
            
    except Exception as e:
        print(f"❌ FFmpeg check failed: {e}")

def check_opencv_backends():
    """Check OpenCV video backend support"""
    print("\n🔍 Checking OpenCV backends...")
    
    try:
        print(f"OpenCV version: {cv2.__version__}")
        
        # Check available backends
        backends = cv2.videoio_registry.getBackends()
        print(f"Available backends: {backends}")
        
        # Check if FFmpeg backend is available
        if cv2.CAP_FFMPEG in backends:
            print("✅ CAP_FFMPEG backend available")
        else:
            print("❌ CAP_FFMPEG backend NOT available")
            
        # Check default backend
        default_backend = cv2.videoio_registry.getBackendName(cv2.CAP_ANY)
        print(f"Default backend: {default_backend}")
        
    except Exception as e:
        print(f"❌ OpenCV backend check failed: {e}")

def test_simple_video_read():
    """Test basic video reading capability"""
    print("\n🔍 Testing basic video reading...")
    
    try:
        # Create a simple test video
        test_cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=1:size=320x240:rate=1',
            '-c:v', 'libx264', '/tmp/test_h264.mp4', '-y'
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Test H.264 video created")
            
            # Try to read with OpenCV
            cap = cv2.VideoCapture('/tmp/test_h264.mp4')
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print("✅ OpenCV can read H.264 videos")
                else:
                    print("❌ OpenCV cannot read frames from H.264")
                cap.release()
            else:
                print("❌ OpenCV cannot open H.264 video file")
                
            # Clean up
            os.remove('/tmp/test_h264.mp4')
        else:
            print("❌ Cannot create test video")
            
    except Exception as e:
        print(f"❌ Video read test failed: {e}")

def check_library_linking():
    """Check if libraries are properly linked"""
    print("\n🔍 Checking library linking...")
    
    try:
        # Check if ffmpeg is linked to AV1 libraries
        result = subprocess.run(['ldd', '/usr/bin/ffmpeg'], capture_output=True, text=True)
        
        av1_libs = ['libdav1d', 'libaom']
        found_libs = []
        
        for lib in av1_libs:
            if lib in result.stdout:
                found_libs.append(lib)
                
        if found_libs:
            print(f"✅ FFmpeg is linked to: {', '.join(found_libs)}")
        else:
            print("❌ FFmpeg is NOT linked to AV1 libraries")
            print("💡 This means FFmpeg was compiled without AV1 support")
            
    except Exception as e:
        print(f"❌ Library linking check failed: {e}")

def main():
    """Run all diagnostic checks"""
    print("🚨 AV1 Production Debug Report")
    print("=" * 50)
    
    check_installed_packages()
    check_ffmpeg_av1_support()
    check_opencv_backends()
    test_simple_video_read()
    check_library_linking()
    
    print("\n" + "=" * 50)
    print("🎯 Diagnosis Summary:")
    print("If you see multiple ❌ markers above, it confirms that")
    print("installing AV1 libraries alone isn't enough.")
    print("\n💡 This is exactly why the smart conversion approach")
    print("is more reliable for production environments!")
    print("\n🚀 Recommendation: Use the prevention + fallback strategy")
    print("that was implemented earlier - it handles these edge cases.")

if __name__ == "__main__":
    main() 