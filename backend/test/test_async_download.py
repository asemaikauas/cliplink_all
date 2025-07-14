#!/usr/bin/env python3
"""
Test script for async parallel YouTube download
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.services.youtube import download_video_async_wrapper, download_video

async def test_async_vs_sync_download():
    """
    Test comparison between async parallel and standard download
    """
    # Test URL - use a shorter video for testing
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - short and reliable
    quality = "720p"  # Use 720p for faster testing
    
    print("🧪 Testing Async Parallel vs Standard Download")
    print(f"📺 Test URL: {test_url}")
    print(f"🎯 Quality: {quality}")
    print("-" * 60)
    
    # Test 1: Async Parallel Download
    print("\n⚡ Testing ASYNC PARALLEL download...")
    start_time = time.time()
    
    try:
        async_path = await download_video_async_wrapper(test_url, quality)
        async_duration = time.time() - start_time
        async_size_mb = async_path.stat().st_size / (1024*1024)
        
        print(f"✅ Async download completed!")
        print(f"   ⏱️  Duration: {async_duration:.1f} seconds")
        print(f"   📁 Size: {async_size_mb:.1f} MB")
        print(f"   📄 File: {async_path.name}")
        
    except Exception as e:
        print(f"❌ Async download failed: {e}")
        async_duration = None
        async_size_mb = None
    
    # Test 2: Standard Download (for comparison)
    print("\n🐌 Testing STANDARD download...")
    start_time = time.time()
    
    try:
        sync_path = download_video(test_url, quality)
        sync_duration = time.time() - start_time
        sync_size_mb = sync_path.stat().st_size / (1024*1024)
        
        print(f"✅ Standard download completed!")
        print(f"   ⏱️  Duration: {sync_duration:.1f} seconds")
        print(f"   📁 Size: {sync_size_mb:.1f} MB") 
        print(f"   📄 File: {sync_path.name}")
        
    except Exception as e:
        print(f"❌ Standard download failed: {e}")
        sync_duration = None
        sync_size_mb = None
    
    # Results comparison
    print("\n" + "="*60)
    print("📊 PERFORMANCE COMPARISON")
    print("="*60)
    
    if async_duration and sync_duration:
        speedup = sync_duration / async_duration
        time_saved = sync_duration - async_duration
        percentage_faster = ((sync_duration - async_duration) / sync_duration) * 100
        
        print(f"⚡ Async Parallel: {async_duration:.1f}s ({async_size_mb:.1f} MB)")
        print(f"🐌 Standard:      {sync_duration:.1f}s ({sync_size_mb:.1f} MB)")
        print(f"🚀 Speedup:       {speedup:.2f}x faster")
        print(f"⏰ Time saved:    {time_saved:.1f} seconds")
        print(f"📈 Improvement:   {percentage_faster:.1f}% faster")
        
        if speedup > 1.5:
            print("🎉 EXCELLENT! Async parallel download is significantly faster!")
        elif speedup > 1.2:
            print("👍 GOOD! Async parallel download shows improvement!")
        else:
            print("🤔 Async parallel download shows minimal improvement")
            
    print("\n🧹 Cleaning up test files...")
    
    # Cleanup test files (optional)
    for file_path in [async_path, sync_path]:
        if 'file_path' in locals() and file_path and file_path.exists():
            try:
                file_path.unlink()
                print(f"   🗑️  Deleted: {file_path.name}")
            except Exception as e:
                print(f"   ⚠️  Could not delete {file_path.name}: {e}")

if __name__ == "__main__":
    print("🚀 Starting Async Parallel Download Test")
    asyncio.run(test_async_vs_sync_download())
    print("✅ Test completed!") 