#!/usr/bin/env python3
"""
Test script to verify Azure Blob Storage integration is working properly.

This script tests:
1. Azure Blob Storage connection
2. Video download and upload to Azure
3. Clip upload functionality
4. Environment configuration

Run this script to verify your Azure integration is working correctly.
"""

import os
import asyncio
import tempfile
from pathlib import Path
import sys

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.azure_storage import AzureBlobStorageService
from app.services.clip_storage import ClipStorageService
from app.services.youtube import download_video


async def test_azure_connection():
    """Test basic Azure Blob Storage connection"""
    print("🔍 Testing Azure Blob Storage connection...")
    
    try:
        azure_service = AzureBlobStorageService()
        
        # Test container creation
        await azure_service.ensure_containers_exist()
        print("✅ Azure containers verified/created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Azure connection failed: {str(e)}")
        return False


async def test_video_download_and_upload():
    """Test video download and Azure upload"""
    print("\n📥 Testing video download and Azure upload...")
    
    try:
        # Test URL (use a short video to minimize test time)
        test_url = "https://youtu.be/dQw4w9WgXcQ"  # Rick Roll - short and always available
        
        print(f"   📺 Downloading test video: {test_url}")
        
        # Download video locally
        video_path = download_video(test_url, "720p")  # Use 720p for faster test
        
        if not video_path.exists():
            raise Exception("Video download failed")
        
        file_size_mb = video_path.stat().st_size / (1024*1024)
        print(f"   ✅ Video downloaded: {video_path.name} ({file_size_mb:.1f} MB)")
        
        # Test Azure upload
        print("   ☁️ Uploading to Azure Blob Storage...")
        
        clip_storage = ClipStorageService(AzureBlobStorageService())
        azure_url = await clip_storage.upload_temp_video_for_processing(
            video_file_path=str(video_path),
            video_id="test_video_123",
            expiry_hours=1  # Short expiry for test
        )
        
        print(f"   ✅ Video uploaded to Azure: {azure_url}")
        
        # Clean up local file
        video_path.unlink()
        print("   🧹 Local test file cleaned up")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Video download/upload test failed: {str(e)}")
        return False


async def test_clip_upload():
    """Test clip upload functionality"""
    print("\n📎 Testing clip upload functionality...")
    
    try:
        # Create a small test video file
        test_clip_content = b"Test video content for Azure upload test"
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            f.write(test_clip_content)
            test_clip_path = f.name
        
        print(f"   📝 Created test clip file: {Path(test_clip_path).name}")
        
        # Test clip upload
        azure_service = AzureBlobStorageService()
        clip_url = await azure_service.upload_file(
            file_path=test_clip_path,
            blob_name="test_clips/test_clip_123.mp4",
            container_type="clips",
            metadata={
                "test": "true",
                "purpose": "integration_test"
            }
        )
        
        print(f"   ✅ Test clip uploaded to Azure: {clip_url}")
        
        # Clean up test file
        os.unlink(test_clip_path)
        print("   🧹 Test clip file cleaned up")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Clip upload test failed: {str(e)}")
        return False


def check_environment():
    """Check environment variables"""
    print("🔧 Checking environment configuration...")
    
    required_vars = [
        "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_ACCOUNT_KEY", 
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_CONTAINER_NAME"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"   ✅ {var}: {'*' * min(len(os.getenv(var)), 20)}...")
    
    if missing_vars:
        print(f"   ❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("   ✅ All required environment variables are set")
    return True


async def main():
    """Run all Azure integration tests"""
    print("🚀 Azure Blob Storage Integration Test")
    print("=" * 50)
    
    # Check environment first
    if not check_environment():
        print("\n❌ Environment check failed. Please set the required Azure environment variables.")
        return False
    
    # Test Azure connection
    if not await test_azure_connection():
        print("\n❌ Azure connection test failed. Check your credentials and network.")
        return False
    
    # Test video download and upload
    if not await test_video_download_and_upload():
        print("\n❌ Video download/upload test failed.")
        return False
    
    # Test clip upload
    if not await test_clip_upload():
        print("\n❌ Clip upload test failed.")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All Azure integration tests passed!")
    print("✅ Your Azure Blob Storage integration is working correctly.")
    print("✅ Videos will now be uploaded to Azure after download.")
    print("✅ Generated clips will be stored in Azure Blob Storage.")
    print("\n💡 Next steps:")
    print("   1. Run your video processing workflow")
    print("   2. Check Azure Storage Explorer to see uploaded files")
    print("   3. Monitor logs for 'Video uploaded to Azure:' messages")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1) 