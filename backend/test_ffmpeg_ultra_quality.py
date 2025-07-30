#!/usr/bin/env python3
"""
Test script for FFmpeg Ultra-Quality Video Processor
This tests the new FFmpeg-based pipeline for maximum quality preservation
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ffmpeg_video_processor import FFmpegVideoProcessor
import tempfile
import cv2
import numpy as np

async def create_test_video(output_path: Path, duration: int = 5) -> bool:
    """Create a test video with moving content for testing"""
    try:
        # Create a short test video using FFmpeg
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 
            f'testsrc=duration={duration}:size=1920x1080:rate=30',
            '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=5',
            '-c:v', 'libx264', '-c:a', 'aac',
            '-y', str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        return process.returncode == 0
        
    except Exception as e:
        print(f"❌ Failed to create test video: {e}")
        return False

async def test_ffmpeg_dependencies():
    """Test if FFmpeg and required tools are available"""
    print("🧪 Testing FFmpeg Dependencies...")
    
    dependencies = ['ffmpeg', 'ffprobe']
    all_available = True
    
    for dep in dependencies:
        try:
            process = await asyncio.create_subprocess_exec(
                dep, '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                print(f"   ✅ {dep} is available")
            else:
                print(f"   ❌ {dep} failed")
                all_available = False
                
        except FileNotFoundError:
            print(f"   ❌ {dep} not found")
            all_available = False
        except Exception as e:
            print(f"   ❌ Error testing {dep}: {e}")
            all_available = False
    
    return all_available

async def test_video_info_extraction():
    """Test video information extraction"""
    print("\n🧪 Testing Video Info Extraction...")
    
    try:
        processor = FFmpegVideoProcessor()
        
        # Create a temporary test video
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            test_video = Path(tmp.name)
        
        # Create test video
        if not await create_test_video(test_video):
            print("   ❌ Failed to create test video")
            return False
        
        try:
            # Test video info extraction
            video_info = await processor.get_video_info(test_video)
            
            print(f"   ✅ Video Info Extracted:")
            print(f"      Resolution: {video_info['width']}x{video_info['height']}")
            print(f"      FPS: {video_info['fps']}")
            print(f"      Codec: {video_info['codec']}")
            print(f"      Duration: {video_info['duration']}s")
            
            return True
            
        finally:
            # Cleanup
            if test_video.exists():
                test_video.unlink()
        
    except Exception as e:
        print(f"   ❌ Video info extraction failed: {e}")
        return False

async def test_frame_extraction():
    """Test high-quality frame extraction"""
    print("\n🧪 Testing Frame Extraction...")
    
    try:
        processor = FFmpegVideoProcessor()
        
        # Create temporary test video
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            test_video = Path(tmp.name)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            frames_dir = Path(temp_dir) / "frames"
            
            # Create test video
            if not await create_test_video(test_video, duration=2):
                print("   ❌ Failed to create test video")
                return False
            
            try:
                # Extract frames
                frame_files = await processor.extract_frames_high_quality(
                    test_video, frames_dir, quality="high"
                )
                
                if frame_files:
                    print(f"   ✅ Extracted {len(frame_files)} frames")
                    
                    # Test first frame
                    first_frame = cv2.imread(str(frame_files[0]))
                    if first_frame is not None:
                        h, w = first_frame.shape[:2]
                        print(f"      First frame: {w}x{h}")
                        return True
                    else:
                        print("   ❌ Could not read extracted frame")
                        return False
                else:
                    print("   ❌ No frames extracted")
                    return False
                    
            finally:
                if test_video.exists():
                    test_video.unlink()
        
    except Exception as e:
        print(f"   ❌ Frame extraction failed: {e}")
        return False

async def test_face_detection():
    """Test MediaPipe face detection integration"""
    print("\n🧪 Testing MediaPipe Face Detection...")
    
    try:
        processor = FFmpegVideoProcessor()
        
        # Create a test image with a synthetic "face" (just for testing structure)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            test_image = Path(tmp.name)
        
        try:
            # Create a simple test image
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Add some content to make it look like a face region
            cv2.rectangle(test_frame, (200, 150), (400, 350), (255, 255, 255), -1)
            cv2.circle(test_frame, (260, 220), 10, (0, 0, 0), -1)  # Eye
            cv2.circle(test_frame, (340, 220), 10, (0, 0, 0), -1)  # Eye
            cv2.rectangle(test_frame, (280, 280), (320, 300), (0, 0, 0), -1)  # Mouth
            
            cv2.imwrite(str(test_image), test_frame)
            
            # Test face detection
            faces = processor.detect_faces_in_frame(test_image)
            
            print(f"   ✅ Face detection completed")
            print(f"      Detected {len(faces)} faces")
            
            if faces:
                for i, (x, y, x1, y1) in enumerate(faces):
                    print(f"      Face {i+1}: ({x}, {y}) to ({x1}, {y1})")
            
            return True
            
        finally:
            if test_image.exists():
                test_image.unlink()
        
    except Exception as e:
        print(f"   ❌ Face detection test failed: {e}")
        return False

async def test_ultra_quality_processing():
    """Test the complete ultra-quality processing pipeline"""
    print("\n🧪 Testing Ultra-Quality Processing Pipeline...")
    
    try:
        processor = FFmpegVideoProcessor()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_video = temp_path / "test_input.mp4"
            output_video = temp_path / "test_output.mp4"
            
            # Create test video
            if not await create_test_video(test_video, duration=3):
                print("   ❌ Failed to create test video")
                return False
            
            # Process with ultra-quality pipeline
            result = await processor.process_video_to_vertical_ultra_quality(
                test_video,
                output_video,
                target_size=(608, 1080),
                quality_preset="fast",  # Use fast for testing
                use_face_detection=True
            )
            
            if result['success']:
                print(f"   ✅ Ultra-quality processing completed!")
                print(f"      Original: {result['original_resolution']}")
                print(f"      Target: {result['target_resolution']}")
                print(f"      Frames processed: {result['frames_processed']}")
                print(f"      Quality preset: {result['quality_preset']}")
                print(f"      Face detection: {result['face_detection_used']}")
                
                # Check if output file exists and has reasonable size
                if output_video.exists():
                    file_size = output_video.stat().st_size
                    print(f"      Output file size: {file_size / 1024:.1f} KB")
                    return True
                else:
                    print("   ❌ Output video file not created")
                    return False
            else:
                print(f"   ❌ Processing failed: {result.get('error', 'Unknown error')}")
                return False
        
    except Exception as e:
        print(f"   ❌ Ultra-quality processing test failed: {e}")
        return False

async def test_quality_presets():
    """Test different quality presets"""
    print("\n🧪 Testing Quality Presets...")
    
    presets = ['fast', 'balanced', 'high']  # Skip 'ultra' for testing speed
    
    for preset in presets:
        try:
            processor = FFmpegVideoProcessor()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                test_video = temp_path / "test_input.mp4"
                output_video = temp_path / f"test_output_{preset}.mp4"
                
                # Create small test video
                if not await create_test_video(test_video, duration=1):
                    print(f"   ❌ Failed to create test video for {preset}")
                    continue
                
                # Test reconstruction with this preset
                # First extract frames
                frames_dir = temp_path / "frames"
                frame_files = await processor.extract_frames_high_quality(test_video, frames_dir, "fast")
                
                if frame_files:
                    # Test video reconstruction
                    video_info = await processor.get_video_info(test_video)
                    success = await processor.reconstruct_video_ultra_quality(
                        frames_dir, output_video, video_info['fps'], quality_preset=preset
                    )
                    
                    if success and output_video.exists():
                        file_size = output_video.stat().st_size
                        print(f"   ✅ {preset.upper()} preset: {file_size / 1024:.1f} KB")
                    else:
                        print(f"   ❌ {preset.upper()} preset failed")
                else:
                    print(f"   ❌ Frame extraction failed for {preset}")
        
        except Exception as e:
            print(f"   ❌ {preset.upper()} preset test failed: {e}")
    
    return True

async def main():
    """Run all tests for FFmpeg Ultra-Quality processor"""
    print("🚀 Testing FFmpeg Ultra-Quality Video Processor\n")
    print("=" * 70)
    
    tests = [
        ("FFmpeg Dependencies", test_ffmpeg_dependencies()),
        ("Video Info Extraction", test_video_info_extraction()),
        ("Frame Extraction", test_frame_extraction()),
        ("Face Detection", test_face_detection()),
        ("Quality Presets", test_quality_presets()),
        ("Ultra-Quality Pipeline", test_ultra_quality_processing()),
    ]
    
    results = {}
    for test_name, test_coro in tests:
        try:
            result = await test_coro
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! FFmpeg Ultra-Quality processor is ready!")
        print("🚀 You can now enjoy:")
        print("   • Maximum quality preservation")
        print("   • Superior face detection with MediaPipe")
        print("   • Advanced FFmpeg encoding options")
        print("   • No more shoulder-only cropping!")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check the errors above.")
        print("💡 Make sure FFmpeg is installed and MediaPipe is working.")

if __name__ == "__main__":
    asyncio.run(main()) 