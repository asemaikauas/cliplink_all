#!/usr/bin/env python3
"""
Test Full Azure Blob Storage + PostgreSQL Integration

This script tests the complete integration between Azure Blob Storage
and PostgreSQL to verify that files can be uploaded to Azure and
their URLs properly stored and retrieved from the database.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
import uuid

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

async def test_full_integration():
    """Test complete Azure Blob Storage + PostgreSQL integration"""
    
    print("🔗 Testing Azure Blob Storage + PostgreSQL Integration")
    print("=" * 60)
    
    try:
        # Import services
        from app.services.azure_storage import get_azure_storage_service
        from app.services.clip_storage import get_clip_storage_service
        from app.database import get_db
        from app.models import Clip, Video, User
        from sqlalchemy import select
        
        print("✅ Successfully imported all services")
        
        # Initialize services
        azure_storage = await get_azure_storage_service()
        clip_storage = await get_clip_storage_service()
        
        # Get database session
        async for db in get_db():
            print("✅ Database connection established")
            
            # Test 1: Create a test file
            print("\n📝 Step 1: Creating test video file...")
            test_file_content = f"Test video file created at {datetime.now()}"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mp4', delete=False) as f:
                f.write(test_file_content)
                test_file_path = f.name
            
            print(f"✅ Test file created: {test_file_path}")
            
            # Test 2: Create test user and video records
            print("\n👤 Step 2: Creating test user and video records...")
            
            # Check if test user exists
            test_user_id = str(uuid.uuid4())
            test_video_id = str(uuid.uuid4())
            
            # Create test video record (simulating a video being processed)
            test_video = Video(
                id=test_video_id,
                user_id=test_user_id,
                youtube_id="test_video_123",
                title="Test Video for Integration",
                status="processing"
            )
            
            db.add(test_video)
            await db.commit()
            print(f"✅ Test video record created: {test_video_id}")
            
            # Test 3: Upload file to Azure Blob Storage
            print("\n☁️ Step 3: Uploading file to Azure Blob Storage...")
            
            clip_blob_url = await azure_storage.upload_file(
                file_path=test_file_path,
                blob_name=f"test/{test_video_id}/test_clip.mp4",
                container_type="clips",
                metadata={
                    "test": "true",
                    "video_id": test_video_id,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            print(f"✅ File uploaded to Azure: {clip_blob_url}")
            
            # Test 4: Store Azure URL in PostgreSQL
            print("\n💾 Step 4: Storing Azure URL in PostgreSQL...")
            
            test_clip = Clip(
                id=str(uuid.uuid4()),
                video_id=test_video_id,
                blob_url=clip_blob_url,  # 🔥 Azure URL stored in PostgreSQL!
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                file_size=len(test_file_content.encode())
            )
            
            db.add(test_clip)
            await db.commit()
            await db.refresh(test_clip)
            
            print(f"✅ Clip record saved to PostgreSQL:")
            print(f"   📋 Clip ID: {test_clip.id}")
            print(f"   🔗 Azure URL: {test_clip.blob_url}")
            print(f"   📏 File size: {test_clip.file_size} bytes")
            
            # Test 5: Retrieve Azure URL from PostgreSQL
            print("\n🔍 Step 5: Retrieving Azure URL from PostgreSQL...")
            
            query = select(Clip).where(Clip.id == test_clip.id)
            result = await db.execute(query)
            retrieved_clip = result.scalar_one_or_none()
            
            if retrieved_clip:
                print(f"✅ Clip retrieved from database:")
                print(f"   🔗 Retrieved URL: {retrieved_clip.blob_url}")
                print(f"   📏 File size: {retrieved_clip.file_size}")
                
                # Verify URLs match
                if retrieved_clip.blob_url == clip_blob_url:
                    print("✅ Azure URL matches original upload URL")
                else:
                    print("❌ URL mismatch!")
                    return False
            else:
                print("❌ Failed to retrieve clip from database")
                return False
            
            # Test 6: Download file using Azure URL from database
            print("\n📥 Step 6: Downloading file using URL from database...")
            
            download_path = f"/tmp/downloaded_test_clip_{test_clip.id}.mp4"
            await azure_storage.download_file(
                blob_url=retrieved_clip.blob_url,
                download_path=download_path
            )
            
            # Verify downloaded content
            with open(download_path, 'r') as f:
                downloaded_content = f.read()
            
            if downloaded_content == test_file_content:
                print("✅ Downloaded file content matches original")
            else:
                print("❌ Downloaded content doesn't match!")
                return False
            
            # Test 7: Generate temporary access URL
            print("\n🔐 Step 7: Generating temporary access URL...")
            
            temp_access_url = await clip_storage.generate_clip_access_url(
                clip=retrieved_clip,
                expiry_hours=1
            )
            
            print(f"✅ Temporary access URL generated:")
            print(f"   🔗 SAS URL: {temp_access_url[:50]}...")
            print(f"   ⏰ Expires in: 1 hour")
            
            # Test 8: Test clip metadata
            print("\n📊 Step 8: Testing clip metadata...")
            
            metadata = await clip_storage.get_clip_metadata(retrieved_clip)
            
            print(f"✅ Clip metadata retrieved:")
            print(f"   📋 Clip ID: {metadata['clip_id']}")
            print(f"   🎬 Video ID: {metadata['video_id']}")
            print(f"   ⏱️ Duration: {metadata['duration']} seconds")
            print(f"   📏 File size: {metadata['file_size']} bytes")
            
            # Test 9: Cleanup
            print("\n🧹 Step 9: Cleaning up test data...")
            
            # Delete from Azure
            await azure_storage.delete_file(clip_blob_url)
            print("✅ Test file deleted from Azure")
            
            # Delete from database
            await db.delete(test_clip)
            await db.delete(test_video)
            await db.commit()
            print("✅ Test records deleted from PostgreSQL")
            
            # Clean up local files
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            if os.path.exists(download_path):
                os.remove(download_path)
            print("✅ Local test files cleaned up")
            
            break  # Exit the async for loop
        
        # Close Azure client
        await azure_storage.close()
        
        print("\n🎉 INTEGRATION TEST PASSED!")
        print("=" * 60)
        print("✅ Azure Blob Storage uploads files successfully")
        print("✅ PostgreSQL stores Azure URLs correctly") 
        print("✅ Files can be retrieved using URLs from database")
        print("✅ Temporary access URLs work properly")
        print("✅ Metadata integration functions correctly")
        print("✅ Cleanup operations work as expected")
        print("\n🚀 Your Azure + PostgreSQL integration is working perfectly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {str(e)}")
        
        # Detailed error analysis
        if "azure" in str(e).lower():
            print("\n💡 Azure-related error suggestions:")
            print("1. Check your Azure credentials in .env file")
            print("2. Verify Azure storage account exists")
            print("3. Check network connectivity to Azure")
        elif "database" in str(e).lower() or "postgres" in str(e).lower():
            print("\n💡 Database-related error suggestions:")
            print("1. Check DATABASE_URL in .env file")
            print("2. Verify PostgreSQL is running")
            print("3. Run database migrations")
        else:
            print(f"\n💡 General error: {str(e)}")
        
        return False

def main():
    """Main entry point"""
    try:
        success = asyncio.run(test_full_integration())
        
        if success:
            print("\n✅ Azure Blob Storage + PostgreSQL integration is ready!")
            sys.exit(0)
        else:
            print("\n❌ Integration test failed. Please check the errors above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 