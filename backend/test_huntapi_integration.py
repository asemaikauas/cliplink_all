#!/usr/bin/env python3
"""
Test script to verify HuntAPI integration as a fallback for Apify
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.huntapi import HuntAPIService, HuntAPIError
from app.services.youtube import YouTubeService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_huntapi_direct():
    """Test HuntAPI service directly"""
    logger.info("🧪 Testing HuntAPI service directly...")
    
    try:
        huntapi = HuntAPIService()
        
        # Test with a simple YouTube video
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll for testing
        
        logger.info(f"Testing HuntAPI with: {test_url}")
        download_url = await huntapi.download_video(test_url, "720p")
        
        logger.info(f"✅ HuntAPI test successful!")
        logger.info(f"📥 Download URL obtained: {download_url[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ HuntAPI direct test failed: {str(e)}")
        return False

async def test_youtube_service_with_fallback():
    """Test YouTube service with HuntAPI fallback"""
    logger.info("🧪 Testing YouTube service with HuntAPI fallback...")
    
    try:
        # Initialize YouTube service (which should also initialize HuntAPI)
        youtube_service = YouTubeService("downloads/test")
        
        # Force Apify to fail by using an invalid token temporarily
        original_token = youtube_service.apify_token
        youtube_service.apify_token = "invalid_token_to_force_failure"
        youtube_service.client = None  # This will cause Apify to fail
        
        # Test with a simple YouTube video
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        logger.info(f"Testing YouTube service fallback with: {test_url}")
        logger.info("(Apify will fail intentionally to trigger HuntAPI fallback)")
        
        downloaded_file = await youtube_service.download_video(test_url, "720p")
        
        logger.info(f"✅ YouTube service fallback test successful!")
        logger.info(f"📁 Downloaded file: {downloaded_file}")
        
        # Restore original token
        youtube_service.apify_token = original_token
        
        return True
        
    except Exception as e:
        logger.error(f"❌ YouTube service fallback test failed: {str(e)}")
        return False

async def test_environment_variables():
    """Test if required environment variables are set"""
    logger.info("🧪 Testing environment variables...")
    
    required_vars = [
        "HUNTAPI_TOKEN",
        "HUNTAPI_KEY",  # Alternative name
        "APIFY_TOKEN"
    ]
    
    available_vars = []
    missing_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            available_vars.append(var)
        else:
            missing_vars.append(var)
    
    logger.info(f"✅ Available environment variables: {available_vars}")
    
    if missing_vars:
        logger.warning(f"⚠️ Missing environment variables: {missing_vars}")
    
    # Check if at least one HuntAPI token is available
    huntapi_available = os.getenv("HUNTAPI_TOKEN") or os.getenv("HUNTAPI_KEY")
    apify_available = os.getenv("APIFY_TOKEN")
    
    if not huntapi_available:
        logger.error("❌ No HuntAPI token found. Set HUNTAPI_TOKEN or HUNTAPI_KEY environment variable.")
        return False
    
    if not apify_available:
        logger.warning("⚠️ No Apify token found. Set APIFY_TOKEN environment variable.")
    
    logger.info("✅ Environment variables check passed")
    return True

async def main():
    """Run all tests"""
    logger.info("🚀 Starting HuntAPI integration tests...")
    
    # Test 1: Environment variables
    env_test = await test_environment_variables()
    if not env_test:
        logger.error("❌ Environment variable test failed. Cannot proceed.")
        return
    
    # Test 2: HuntAPI direct test
    huntapi_test = await test_huntapi_direct()
    
    # Test 3: YouTube service fallback test (only if HuntAPI works)
    if huntapi_test:
        fallback_test = await test_youtube_service_with_fallback()
    else:
        logger.warning("⏭️ Skipping YouTube service fallback test due to HuntAPI failure")
        fallback_test = False
    
    # Summary
    logger.info("📊 Test Results Summary:")
    logger.info(f"  Environment Variables: {'✅ PASS' if env_test else '❌ FAIL'}")
    logger.info(f"  HuntAPI Direct: {'✅ PASS' if huntapi_test else '❌ FAIL'}")
    logger.info(f"  YouTube Fallback: {'✅ PASS' if fallback_test else '❌ FAIL'}")
    
    if all([env_test, huntapi_test, fallback_test]):
        logger.info("🎉 All tests passed! HuntAPI integration is working correctly.")
    else:
        logger.error("⚠️ Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main()) 