#!/usr/bin/env python3
"""
Test Azure Blob Storage Connection

This script tests your Azure Blob Storage configuration to ensure
everything is set up correctly before running the full application.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables from .env file
from dotenv import load_dotenv 


load_dotenv()
# Load Azure environment variables
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")


async def test_azure_connection():
    """Test Azure Blob Storage connection and operations"""
    
    print("🧪 Testing Azure Blob Storage Connection...")
    print("=" * 50)
    
    # Check environment variables
    env_vars = {
        "AZURE_STORAGE_ACCOUNT_NAME": AZURE_STORAGE_ACCOUNT_NAME,
        "AZURE_STORAGE_ACCOUNT_KEY": AZURE_STORAGE_ACCOUNT_KEY,
        "AZURE_STORAGE_CONNECTION_STRING": AZURE_STORAGE_CONNECTION_STRING,
        "AZURE_STORAGE_CONTAINER_NAME": AZURE_STORAGE_CONTAINER_NAME
    }
    
    print("📋 Checking environment variables...")
    missing_vars = []
    for var_name, value in env_vars.items():
        if not value:
            missing_vars.append(var_name)
            print(f"❌ {var_name}: Not set")
        else:
            # Show partial value for security
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var_name}: {display_value}")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your backend/.env file")
        return False
    
    try:
        # Test Azure Blob Storage connection
        print("\n🔗 Testing Azure Blob Storage connection...")
        
        from app.services.azure_storage import get_azure_storage_service
        
        azure_storage = await get_azure_storage_service()
        
        # Test connection by listing containers
        print("📁 Ensuring containers exist...")
        await azure_storage.ensure_containers_exist()
        print("✅ Containers created/verified successfully")
        
        # Test file upload with a small test file
        print("📤 Testing file upload...")
        
        # Create a small test file
        test_file_path = "/tmp/azure_test.txt"
        with open(test_file_path, "w") as f:
            f.write("Azure Blob Storage test file - you can delete this")
        
        # Upload test file
        test_blob_url = await azure_storage.upload_file(
            file_path=test_file_path,
            blob_name="test/azure_connection_test.txt",
            container_type="temp"
        )
        print(f"✅ Test file uploaded: {test_blob_url}")
        
        # Test file download
        print("📥 Testing file download...")
        download_path = "/tmp/azure_test_download.txt"
        await azure_storage.download_file(test_blob_url, download_path)
        
        # Verify download
        if os.path.exists(download_path):
            with open(download_path, "r") as f:
                content = f.read()
            if "Azure Blob Storage test" in content:
                print("✅ Test file downloaded and verified")
            else:
                print("❌ Downloaded file content doesn't match")
                return False
        else:
            print("❌ Downloaded file not found")
            return False
        
        # Test file deletion
        print("🗑️ Testing file deletion...")
        deleted = await azure_storage.delete_file(test_blob_url)
        if deleted:
            print("✅ Test file deleted successfully")
        else:
            print("⚠️ Test file deletion failed (file may not exist)")
        
        # Clean up local test files
        for file_path in [test_file_path, download_path]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Close Azure client
        await azure_storage.close()
        
        print("\n🎉 All Azure Blob Storage tests passed!")
        print("Your Azure configuration is working correctly.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Azure Blob Storage test failed: {str(e)}")
        
        # Common error suggestions
        if "authentication" in str(e).lower():
            print("\n💡 Authentication Error Suggestions:")
            print("1. Check your AZURE_STORAGE_ACCOUNT_KEY is correct")
            print("2. Verify your AZURE_STORAGE_CONNECTION_STRING is complete")
            print("3. Make sure your storage account name is correct")
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            print("\n💡 Network Error Suggestions:")
            print("1. Check your internet connection")
            print("2. Verify Azure storage account is in the correct region")
            print("3. Check if there are firewall restrictions")
        elif "container" in str(e).lower():
            print("\n💡 Container Error Suggestions:")
            print("1. Storage account might not exist")
            print("2. Check permissions on the storage account")
            
        return False

def main():
    """Main entry point"""
    try:
        success = asyncio.run(test_azure_connection())
        
        if success:
            print("\n✅ Azure Blob Storage is ready for Cliplink!")
            sys.exit(0)
        else:
            print("\n❌ Azure Blob Storage configuration needs attention.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 