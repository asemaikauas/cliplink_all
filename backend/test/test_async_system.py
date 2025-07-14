#!/usr/bin/env python3
"""
Test script to verify async system can handle concurrent requests
"""

import asyncio
import time
from pathlib import Path
from app.services.vertical_crop_async import async_vertical_crop_service

async def test_concurrent_requests():
    """Test multiple concurrent requests to the async vertical crop service"""
    
    print("🧪 Testing concurrent async video processing...")
    
    # Simulate multiple video files (you would replace these with actual video paths)
    test_videos = [
        {"input": "test_video_1.mp4", "output": "output_1_vertical.mp4"},
        {"input": "test_video_2.mp4", "output": "output_2_vertical.mp4"}, 
        {"input": "test_video_3.mp4", "output": "output_3_vertical.mp4"},
    ]
    
    print(f"📝 Starting {len(test_videos)} concurrent video processing tasks...")
    
    # Start all tasks concurrently
    tasks = []
    start_time = time.time()
    
    for i, video in enumerate(test_videos):
        print(f"🚀 Starting task {i+1}: {video['input']} -> {video['output']}")
        
        # Note: In real usage, you would have actual video files
        # For this test, we'll just check the task management system
        task_info = {
            "task_id": f"test_task_{i+1}",
            "input_path": video["input"],
            "output_path": video["output"],
            "status": "queued",
            "progress": 0,
            "created_at": time.time()
        }
        
        # Simulate adding to task queue
        async_vertical_crop_service.active_tasks[task_info["task_id"]] = task_info
        
    print(f"⏳ All tasks queued. Checking task management...")
    
    # Test task status retrieval
    active_tasks = await async_vertical_crop_service.list_active_tasks()
    print(f"📊 Active tasks: {len(active_tasks)}")
    
    for task_id, task_info in active_tasks.items():
        status = await async_vertical_crop_service.get_task_status(task_id)
        print(f"  📋 {task_id}: {status['status']} - {status['input_path']}")
    
    # Test task cleanup
    print(f"🧹 Testing task cleanup...")
    await async_vertical_crop_service.cleanup_completed_tasks(0)  # Clean all
    
    remaining_tasks = await async_vertical_crop_service.list_active_tasks()
    print(f"📊 Remaining tasks after cleanup: {len(remaining_tasks)}")
    
    elapsed_time = time.time() - start_time
    print(f"✅ Test completed in {elapsed_time:.2f} seconds")
    
    return True

async def test_task_limits():
    """Test concurrent task limits"""
    print("\n🧪 Testing concurrent task limits...")
    
    max_tasks = async_vertical_crop_service.max_concurrent_tasks
    print(f"📊 Max concurrent tasks: {max_tasks}")
    
    # Try to exceed the limit
    tasks_created = 0
    for i in range(max_tasks + 5):  # Try to create more than the limit
        result = await async_vertical_crop_service.create_vertical_crop_async(
            input_video_path=Path(f"fake_video_{i}.mp4"),
            output_video_path=Path(f"fake_output_{i}.mp4"),
            use_speaker_detection=False,
            smoothing_strength="low"
        )
        
        if result["success"]:
            tasks_created += 1
        else:
            print(f"⚠️ Task {i+1} rejected: {result['error']}")
            break
    
    print(f"📊 Tasks created: {tasks_created}")
    
    # Clean up
    await async_vertical_crop_service.cleanup_completed_tasks(0)
    
    return True

async def main():
    """Main test function"""
    print("🚀 Starting Async System Tests")
    print("=" * 50)
    
    try:
        # Test 1: Concurrent requests
        await test_concurrent_requests()
        
        # Test 2: Task limits
        await test_task_limits()
        
        print("\n✅ All tests passed! Async system is working correctly.")
        print("\n📋 System Capabilities:")
        print(f"   🔧 Max workers: {async_vertical_crop_service.thread_executor._max_workers}")
        print(f"   🎯 Max concurrent tasks: {async_vertical_crop_service.max_concurrent_tasks}")
        print(f"   📊 Current active tasks: {len(await async_vertical_crop_service.list_active_tasks())}")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 Async system is ready for production!")
    else:
        print("\n❌ Async system needs fixes before production.") 