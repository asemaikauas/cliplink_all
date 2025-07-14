#!/usr/bin/env python3
"""
Scheduled Cleanup Script for Temporary Videos

This script should be run periodically (e.g., via cron) to clean up
expired temporary videos from Azure Blob Storage.

Usage:
    python scripts/cleanup_temp_videos.py

Environment Variables:
    - All Azure Blob Storage configuration variables
    - DATABASE_URL for database connection
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from app.services.azure_storage import get_azure_storage_service
from app.services.clip_storage import get_clip_storage_service
from app.database import get_db


async def cleanup_expired_videos():
    """
    Main cleanup function
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize services
        azure_storage = await get_azure_storage_service()
        clip_storage = await get_clip_storage_service()
        
        logger.info("Starting scheduled cleanup of expired temporary videos")
        
        # Run cleanup
        deleted_count = await azure_storage.cleanup_expired_temp_videos()
        
        logger.info(f"Cleanup completed: deleted {deleted_count} expired temporary videos")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise
    finally:
        # Close Azure storage client
        if azure_storage:
            await azure_storage.close()


def setup_logging():
    """
    Setup logging configuration
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/var/log/cliplink/cleanup.log', mode='a')
        ]
    )


async def main():
    """
    Main entry point
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        deleted_count = await cleanup_expired_videos()
        
        print(f"Cleanup completed successfully. Deleted {deleted_count} expired videos.")
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Cleanup script failed: {str(e)}")
        print(f"Cleanup failed: {str(e)}", file=sys.stderr)
        
        # Exit with error
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 