#!/usr/bin/env python3
"""Test script for audio extraction and transcription fix."""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.routers.subtitles import extract_audio_for_transcription
from app.services.groq_client import transcribe


async def test_audio_extraction():
    """Test the audio extraction functionality."""
    print("🎵 Testing Audio Extraction Fix")
    print("=" * 50)
    
    # Check if we have any video files to test with
    test_files = [
        "test_video.mp4",
        "sample.mp4", 
        "example.mov",
        "demo.avi"
    ]
    
    video_file = None
    for test_file in test_files:
        if os.path.exists(test_file):
            video_file = test_file
            break
    
    if not video_file:
        print("⚠️ No test video files found. Please provide a video file to test with.")
        print("Expected files:", test_files)
        return False
    
    print(f"📁 Using test video file: {video_file}")
    
    try:
        # Test audio extraction
        task_id = "test_extraction_123"
        
        print(f"\n🎵 Step 1: Extracting audio from video...")
        audio_file_path = await extract_audio_for_transcription(video_file, task_id)
        
        if not audio_file_path or not Path(audio_file_path).exists():
            print("❌ Audio extraction failed - no audio file created")
            return False
        
        # Check audio file properties
        file_size = os.path.getsize(audio_file_path)
        print(f"✅ Audio extracted: {audio_file_path}")
        print(f"📊 Audio file size: {file_size / (1024*1024):.2f} MB")
        
        # Test transcription with extracted audio
        print(f"\n🎤 Step 2: Testing transcription with extracted audio...")
        
        try:
            transcription_result = transcribe(
                file_path=audio_file_path,
                apply_vad=False,  # Disable VAD for initial test
                task_id=task_id
            )
            
            print(f"✅ Transcription successful!")
            print(f"📊 Results:")
            print(f"   - Segments: {len(transcription_result['segments'])}")
            print(f"   - Language: {transcription_result['language']}")
            print(f"   - Word timestamps: {len(transcription_result.get('word_timestamps', []))}")
            print(f"   - Cost: ${transcription_result['cost_usd']:.4f}")
            print(f"   - Latency: {transcription_result['latency_ms']}ms")
            
            # Show first few segments
            if transcription_result['segments']:
                print(f"\n📝 First 3 transcription segments:")
                for i, segment in enumerate(transcription_result['segments'][:3], 1):
                    if hasattr(segment, 'text'):
                        text = segment.text
                        start = segment.start
                        end = segment.end
                    else:
                        text = segment.get('text', '')
                        start = segment.get('start', 0)
                        end = segment.get('end', 0)
                    
                    print(f"   {i}. [{start:.2f}s - {end:.2f}s] '{text}'")
            
            success = True
            
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            success = False
        
        # Clean up extracted audio file
        try:
            os.remove(audio_file_path)
            print(f"🧹 Cleaned up temporary audio file")
        except Exception as e:
            print(f"⚠️ Failed to clean up audio file: {e}")
        
        return success
        
    except Exception as e:
        print(f"❌ Audio extraction test failed: {e}")
        return False


async def test_video_without_audio():
    """Test handling of video files without audio tracks."""
    print("\n\n🔇 Testing Video Without Audio Track")
    print("=" * 50)
    
    # This would require creating a test video without audio
    # For now, just document the expected behavior
    print("📋 Expected behavior for videos without audio:")
    print("   1. Audio extraction should detect no audio track")
    print("   2. Should provide clear error message")
    print("   3. Should not create empty audio files")
    print("   4. Should fail gracefully without crashing")
    
    print("\n⚠️ To test this, provide a video file without an audio track")
    return True


async def main():
    """Main test runner."""
    print("🧪 Audio Extraction & Transcription Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Audio extraction and transcription
        test1_success = await test_audio_extraction()
        
        # Test 2: Video without audio (documentation for now)
        test2_success = await test_video_without_audio()
        
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        print(f"   Audio Extraction & Transcription: {'✅ PASS' if test1_success else '❌ FAIL'}")
        print(f"   Video Without Audio Handling: {'✅ DOCUMENTED' if test2_success else '❌ FAIL'}")
        
        if test1_success:
            print("\n🎉 Audio extraction fix appears to be working!")
            print("💡 The 'no audio track found' error should now be resolved.")
        else:
            print("\n❌ Tests failed. The audio extraction may need more work.")
        
        print("\n📋 Next Steps:")
        print("   1. Start the uvicorn server: uvicorn app.main:app --reload")
        print("   2. Test with API: curl -X POST 'http://localhost:8000/subtitles' -F 'video_file=@your_video.mp4'")
        print("   3. Try with speech_sync=true for best results")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test1_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 