#!/usr/bin/env python3
"""
Test script to verify conda-forge OpenCV AV1 support
Run this after building the Docker container with conda-forge OpenCV
"""

import cv2
import sys
import subprocess
import json
from pathlib import Path

def test_opencv_build_info():
    """Check OpenCV build information for codec support"""
    print("🔍 OpenCV Build Information:")
    print(f"   Version: {cv2.__version__}")
    
    # Get build information
    build_info = cv2.getBuildInformation()
    
    # Check for key AV1-related components
    av1_indicators = [
        "libavcodec", "libavformat", "libavutil", "libswscale",
        "dav1d", "aom", "ffmpeg"
    ]
    
    print("\n🔧 Codec Support Indicators:")
    for indicator in av1_indicators:
        if indicator.lower() in build_info.lower():
            print(f"   ✅ {indicator}: Found")
        else:
            print(f"   ❌ {indicator}: Not found")
    
    return build_info

def test_video_codecs():
    """Test which video codecs OpenCV can handle"""
    print("\n🎬 Testing Video Codec Support:")
    
    # Common video codecs
    test_codecs = [
        ("H.264", "avc1"),
        ("H.265", "hevc"), 
        ("VP9", "vp09"),
        ("AV1", "av01")
    ]
    
    for name, fourcc in test_codecs:
        try:
            # Test if we can create a VideoWriter with this codec
            fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
            print(f"   {name}: VideoWriter fourcc available")
        except Exception as e:
            print(f"   {name}: Not available ({e})")

def test_av1_video_file(video_path: str):
    """Test reading an actual AV1 video file if provided"""
    if not Path(video_path).exists():
        print(f"\n⚠️ Test video not found: {video_path}")
        return False
    
    print(f"\n🎯 Testing AV1 video file: {video_path}")
    
    # First check codec with ffprobe
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_streams', '-select_streams', 'v:0',
            '-print_format', 'json', video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            if streams:
                codec_name = streams[0].get('codec_name', 'unknown')
                print(f"   📄 Detected codec: {codec_name}")
        
    except Exception as e:
        print(f"   ⚠️ Could not probe video: {e}")
    
    # Test OpenCV reading
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"   ❌ OpenCV cannot open video file")
        return False
    
    # Try to read some frames
    frames_tested = 0
    successful_reads = 0
    
    for i in range(20):  # Test first 20 frames
        ret, frame = cap.read()
        frames_tested += 1
        
        if ret and frame is not None:
            successful_reads += 1
        elif not ret:
            break
    
    cap.release()
    
    success_rate = successful_reads / frames_tested if frames_tested > 0 else 0
    
    print(f"   📊 Frame read success: {successful_reads}/{frames_tested} ({success_rate:.1%})")
    
    if success_rate >= 0.9:
        print(f"   ✅ OpenCV can read AV1 video excellently!")
        return True
    elif success_rate >= 0.5:
        print(f"   ⚠️ OpenCV can read AV1 video but with some issues")
        return True
    else:
        print(f"   ❌ OpenCV cannot read AV1 video properly")
        return False

def main():
    print("🧪 Testing conda-forge OpenCV AV1 Support\n")
    
    # Test 1: OpenCV build info
    build_info = test_opencv_build_info()
    
    # Test 2: Codec support
    test_video_codecs()
    
    # Test 3: Actual AV1 file (if provided)
    if len(sys.argv) > 1:
        test_av1_video_file(sys.argv[1])
    else:
        print("\n💡 To test with an actual AV1 video file:")
        print("   python test_av1_support.py /path/to/av1_video.mp4")
    
    print("\n🎯 Test complete!")
    
    # Save build info for debugging
    with open("opencv_build_info.txt", "w") as f:
        f.write(build_info)
    print("📄 Full build info saved to opencv_build_info.txt")

if __name__ == "__main__":
    main() 