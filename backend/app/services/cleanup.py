"""
Aggressive Cleanup Service

This service ensures local files are cleaned up to prevent infinite storage growth.
Since local storage is used as temporary workspace for video processing, we need
aggressive cleanup to prevent disk space issues.
"""

import os
import time
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CleanupService:
    """
    Service for aggressive cleanup of temporary files
    """
    
    def __init__(self):
        self.base_dirs = [
            Path("downloads"),
            Path("temp_uploads"),
            Path("clips"),
            Path("thumbnails")
        ]
        self.max_file_age_hours = int(os.getenv("CLEANUP_MAX_FILE_AGE_HOURS", "2"))
        self.aggressive_cleanup_enabled = os.getenv("AGGRESSIVE_CLEANUP", "true").lower() == "true"
        
    async def cleanup_old_files(self, max_age_hours: Optional[int] = None) -> int:
        """
        Clean up files older than specified hours
        
        Args:
            max_age_hours: Maximum age in hours (default: from env var)
            
        Returns:
            Number of files deleted
        """
        if not self.aggressive_cleanup_enabled:
            logger.info("Aggressive cleanup is disabled")
            return 0
            
        max_age = max_age_hours or self.max_file_age_hours
        cutoff_time = time.time() - (max_age * 3600)
        deleted_count = 0
        
        logger.info(f"Starting cleanup of files older than {max_age} hours")
        
        for base_dir in self.base_dirs:
            if not base_dir.exists():
                continue
                
            try:
                for file_path in base_dir.rglob("*"):
                    if file_path.is_file():
                        try:
                            if file_path.stat().st_mtime < cutoff_time:
                                file_path.unlink()
                                deleted_count += 1
                                logger.debug(f"Deleted old file: {file_path}")
                        except (OSError, PermissionError) as e:
                            logger.warning(f"Could not delete {file_path}: {e}")
                            
            except Exception as e:
                logger.error(f"Error cleaning directory {base_dir}: {e}")
                
        logger.info(f"Cleanup completed: deleted {deleted_count} old files")
        return deleted_count
    
    async def cleanup_specific_video(self, video_id: str) -> int:
        """
        Clean up all files related to a specific video
        
        Args:
            video_id: Video ID to clean up
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        
        for base_dir in self.base_dirs:
            if not base_dir.exists():
                continue
                
            try:
                # Look for files containing the video_id
                for file_path in base_dir.rglob(f"*{video_id}*"):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            logger.debug(f"Deleted video file: {file_path}")
                        except (OSError, PermissionError) as e:
                            logger.warning(f"Could not delete {file_path}: {e}")
                            
            except Exception as e:
                logger.error(f"Error cleaning video {video_id} from {base_dir}: {e}")
                
        logger.info(f"Cleaned up {deleted_count} files for video {video_id}")
        return deleted_count
    
    async def cleanup_empty_directories(self) -> int:
        """
        Remove empty directories in the base directories
        
        Returns:
            Number of directories removed
        """
        removed_count = 0
        
        for base_dir in self.base_dirs:
            if not base_dir.exists():
                continue
                
            try:
                # Walk directories bottom-up to remove empty ones
                for dir_path in reversed(list(base_dir.rglob("*"))):
                    if dir_path.is_dir() and not any(dir_path.iterdir()):
                        try:
                            dir_path.rmdir()
                            removed_count += 1
                            logger.debug(f"Removed empty directory: {dir_path}")
                        except (OSError, PermissionError) as e:
                            logger.warning(f"Could not remove directory {dir_path}: {e}")
                            
            except Exception as e:
                logger.error(f"Error removing empty directories from {base_dir}: {e}")
                
        if removed_count > 0:
            logger.info(f"Removed {removed_count} empty directories")
        return removed_count
    
    async def get_storage_usage(self) -> dict:
        """
        Get current storage usage statistics
        
        Returns:
            Dictionary with storage usage info
        """
        usage = {
            "total_files": 0,
            "total_size_mb": 0,
            "directories": {}
        }
        
        for base_dir in self.base_dirs:
            if not base_dir.exists():
                usage["directories"][str(base_dir)] = {"files": 0, "size_mb": 0}
                continue
                
            dir_files = 0
            dir_size = 0
            
            try:
                for file_path in base_dir.rglob("*"):
                    if file_path.is_file():
                        dir_files += 1
                        dir_size += file_path.stat().st_size
                        
            except Exception as e:
                logger.error(f"Error calculating usage for {base_dir}: {e}")
                
            usage["directories"][str(base_dir)] = {
                "files": dir_files,
                "size_mb": round(dir_size / (1024 * 1024), 2)
            }
            
            usage["total_files"] += dir_files
            usage["total_size_mb"] += usage["directories"][str(base_dir)]["size_mb"]
            
        usage["total_size_mb"] = round(usage["total_size_mb"], 2)
        return usage
    
    async def aggressive_cleanup_after_processing(self, video_path: Path, task_id: str) -> int:
        """
        Perform aggressive cleanup after video processing is complete
        
        Args:
            video_path: Path to the source video file
            task_id: Task ID for tracking
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        
        # Delete the source video file
        if video_path and video_path.exists():
            try:
                video_path.unlink()
                deleted_count += 1
                logger.info(f"Deleted source video: {video_path}")
            except Exception as e:
                logger.warning(f"Could not delete source video {video_path}: {e}")
        
        # Clean up any temp files related to this task
        for base_dir in self.base_dirs:
            if not base_dir.exists():
                continue
                
            try:
                for file_path in base_dir.rglob(f"*{task_id}*"):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            logger.debug(f"Deleted task file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not delete {file_path}: {e}")
                            
            except Exception as e:
                logger.error(f"Error cleaning task {task_id} from {base_dir}: {e}")
        
        # Clean up empty directories
        await self.cleanup_empty_directories()
        
        logger.info(f"Aggressive cleanup for task {task_id}: deleted {deleted_count} files")
        return deleted_count


# Global instance
cleanup_service = CleanupService()


async def get_cleanup_service() -> CleanupService:
    """Dependency injection for cleanup service"""
    return cleanup_service 