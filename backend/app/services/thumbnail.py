"""
Thumbnail generation service for video clips
Extracts frames from videos using FFmpeg at the 1-second mark
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)

async def generate_thumbnail(
    video_path: Path,
    output_dir: Path,
    clip_id: str,
    width: int = 200,
    timestamp: float = 1.0
) -> Dict[str, Any]:
    """
    Generate a thumbnail from a video at the specified timestamp
    
    Args:
        video_path: Path to the source video file
        output_dir: Directory to save thumbnails
        clip_id: Unique identifier for the clip
        width: Desired thumbnail width (height calculated automatically)
        timestamp: Time in seconds to extract frame from (default: 1.0s)
    
    Returns:
        Dict with success status, thumbnail_path, and error info
    """
    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate thumbnail filename
        thumbnail_filename = f"{clip_id}.jpg"
        thumbnail_path = output_dir / thumbnail_filename
        
        # Build FFmpeg command
        # -ss: seek to timestamp before input (faster)
        # -i: input video
        # -vframes 1: extract only one frame
        # -vf scale: resize to specified width, auto-calculate height
        # -q:v 2: high quality JPEG (1-31, lower is better)
        # -y: overwrite output file
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-ss', str(timestamp),
            '-i', str(video_path),
            '-vframes', '1',
            '-vf', f'scale={width}:-1',
            '-q:v', '2',
            '-y',
            str(thumbnail_path)
        ]
        
        logger.info(f"🖼️ Generating thumbnail for {clip_id} at {timestamp}s...")
        
        # Run FFmpeg asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            # Verify thumbnail was created
            if thumbnail_path.exists() and thumbnail_path.stat().st_size > 0:
                logger.info(f"✅ Thumbnail generated: {thumbnail_filename}")
                return {
                    "success": True,
                    "thumbnail_path": str(thumbnail_path),
                    "thumbnail_filename": thumbnail_filename,
                    "relative_path": f"thumbnails/{thumbnail_filename}",
                    "file_size": thumbnail_path.stat().st_size
                }
            else:
                raise Exception("Thumbnail file was not created or is empty")
        else:
            error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
            raise Exception(f"FFmpeg failed with code {process.returncode}: {error_msg}")
            
    except Exception as e:
        logger.error(f"❌ Thumbnail generation failed for {clip_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "thumbnail_path": None,
            "thumbnail_filename": None
        }

async def generate_thumbnails_batch(
    video_paths: list[Path],
    output_dir: Path,
    clip_ids: list[str],
    width: int = 200,
    timestamp: float = 1.0
) -> Dict[str, Dict[str, Any]]:
    """
    Generate thumbnails for multiple videos in parallel
    
    Args:
        video_paths: List of video file paths
        output_dir: Directory to save thumbnails
        clip_ids: List of unique identifiers for each clip
        width: Desired thumbnail width
        timestamp: Time in seconds to extract frame from
    
    Returns:
        Dict mapping clip_id to thumbnail generation result
    """
    if len(video_paths) != len(clip_ids):
        raise ValueError("video_paths and clip_ids must have the same length")
    
    # Create tasks for parallel processing
    tasks = []
    for video_path, clip_id in zip(video_paths, clip_ids):
        task = generate_thumbnail(video_path, output_dir, clip_id, width, timestamp)
        tasks.append(task)
    
    # Run all thumbnail generations in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Build result dictionary
    thumbnail_results = {}
    for clip_id, result in zip(clip_ids, results):
        if isinstance(result, Exception):
            thumbnail_results[clip_id] = {
                "success": False,
                "error": str(result),
                "thumbnail_path": None
            }
        else:
            thumbnail_results[clip_id] = result
    
    successful_count = sum(1 for r in thumbnail_results.values() if r.get("success", False))
    logger.info(f"🖼️ Batch thumbnail generation complete: {successful_count}/{len(clip_ids)} successful")
    
    return thumbnail_results

def cleanup_old_thumbnails(thumbnail_dir: Path, max_age_days: int = 7):
    """
    Clean up old thumbnail files
    
    Args:
        thumbnail_dir: Directory containing thumbnails
        max_age_days: Remove files older than this many days
    """
    try:
        if not thumbnail_dir.exists():
            return
        
        import time
        current_time = time.time()
        cutoff_time = current_time - (max_age_days * 24 * 60 * 60)
        
        removed_count = 0
        for thumbnail_file in thumbnail_dir.glob("*.jpg"):
            if thumbnail_file.stat().st_mtime < cutoff_time:
                thumbnail_file.unlink()
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"🧹 Cleaned up {removed_count} old thumbnails")
            
    except Exception as e:
        logger.error(f"❌ Thumbnail cleanup failed: {e}") 