"""
Segment-aware video download service for ClipLink with Azure temp storage integration
Downloads only necessary video segments based on timecodes and stores them in Azure temp storage
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient
import os
from dotenv import load_dotenv
import time

load_dotenv()
logger = logging.getLogger(__name__)

class SegmentDownloadService:
    """
    Service for downloading specific video segments instead of full videos
    Now integrates with Azure temp storage for the optimized workflow
    """
    
    def __init__(self):
        self.apify_token = os.getenv("APIFY_TOKEN")
        if not self.apify_token:
            raise ValueError("APIFY_TOKEN environment variable not set")
        self.client = ApifyClient(self.apify_token)
        self.local_downloads_dir = Path("downloads/segments")
        self.local_downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Import Azure storage for temp storage integration
        self.azure_storage = None
        self._azure_initialized = False
    
    async def _ensure_azure_storage(self):
        """Initialize Azure storage service if not already done"""
        if not self._azure_initialized:
            try:
                from .azure_storage import get_azure_storage_service
                self.azure_storage = await get_azure_storage_service()
                await self.azure_storage.ensure_containers_exist()
                self._azure_initialized = True
                logger.info("✅ Azure storage initialized for segment downloads")
            except Exception as e:
                logger.warning(f"⚠️ Azure storage initialization failed: {e}")
                self.azure_storage = None
    
    async def download_video_segments_with_azure_temp_storage(
        self, 
        youtube_url: str, 
        viral_segments: List[Dict[str, Any]], 
        quality: str = "1080p",
        video_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Download segments and store them in Azure temp storage for processing
        
        This follows the user's requirement #3:
        "Download only necessary parts based on Gemini timecodes → Azure temp storage"
        
        Returns:
            List of segment info with both local paths and Azure temp URLs
        """
        try:
            logger.info(f"🎯 Starting optimized segment download with Azure temp storage for {len(viral_segments)} segments")
            
            # Initialize Azure storage
            await self._ensure_azure_storage()
            
            # Step 1: Get download URL from Apify (without downloading full video)
            download_url = await self._get_video_download_url(youtube_url, quality)
            
            # Step 2: Download segments in parallel
            segment_tasks = []
            for i, segment in enumerate(viral_segments):
                task = self._download_and_upload_single_segment(
                    download_url=download_url,
                    segment_index=i,
                    start_time=segment['start'],
                    end_time=segment['end'],
                    segment_title=segment.get('title', f'segment_{i+1}'),
                    quality=quality,
                    video_id=video_id or "unknown"
                )
                segment_tasks.append(task)
            
            # Wait for all segments to download and upload (using batch processing to avoid overwhelming APIs)
            segment_results = await self._process_downloads_in_batches(segment_tasks, batch_size=3)
            
            # Filter out failed downloads
            successful_segments = []
            failed_count = 0
            
            for i, result in enumerate(segment_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Segment {i+1} failed: {result}")
                    failed_count += 1
                elif isinstance(result, dict) and result.get("success"):
                    successful_segments.append(result)
                else:
                    logger.error(f"❌ Segment {i+1} failed: {result}")
                    failed_count += 1
            
            total_size_mb = sum(seg.get("file_size_mb", 0) for seg in successful_segments)
            
            logger.info(f"✅ Successfully processed {len(successful_segments)}/{len(viral_segments)} segments")
            logger.info(f"💾 Total size: {total_size_mb:.1f} MB")
            logger.info(f"☁️ Azure temp storage: {len([s for s in successful_segments if s.get('azure_temp_url')])} uploaded")
            
            return successful_segments
            
        except Exception as e:
            logger.error(f"Segment download with Azure temp storage failed: {str(e)}")
            raise
    
    async def _download_and_upload_single_segment(
        self,
        download_url: str,
        segment_index: int,
        start_time: float,
        end_time: float,
        segment_title: str,
        quality: str,
        video_id: str
    ) -> Dict[str, Any]:
        """
        Download a single segment and upload to Azure temp storage
        
        This implements the user's workflow requirement:
        "Download only necessary parts → Azure temp storage"
        """
        try:
            # Sanitize filename using proper Unicode handling (same as above)
            import unicodedata
            import re
            
            # Convert Unicode characters (like Cyrillic) to ASCII equivalents
            try:
                safe_title = unicodedata.normalize('NFKD', segment_title)
                safe_title = safe_title.encode('ascii', 'ignore').decode('ascii')
            except Exception:
                # Fallback: remove non-ASCII characters
                safe_title = ''.join(char for char in segment_title if ord(char) < 128)
            
            # Keep only safe characters and replace spaces
            safe_title = re.sub(r'[^a-zA-Z0-9\-_]', '_', safe_title).strip('_')
            safe_title = re.sub(r'[_]+', '_', safe_title)  # Multiple underscores -> single
            
            # Ensure it's not empty
            if not safe_title:
                safe_title = f"segment_{segment_index+1}"
            
            # Limit length for filesystem compatibility
            if len(safe_title) > 100:
                safe_title = safe_title[:100].rstrip('_')
            
            duration = end_time - start_time
            local_output_path = self.local_downloads_dir / f"{safe_title}_{segment_index+1}_{quality}.mp4"
            
            logger.info(f"📥 Downloading segment {segment_index+1}: {safe_title} ({start_time:.1f}s-{end_time:.1f}s)")
            logger.info(f"📝 Original title: '{segment_title}' → Safe title: '{safe_title}'")
            
            # FFmpeg command to download specific segment
            cmd = [
                'ffmpeg',
                '-hide_banner', '-loglevel', 'error',
                '-ss', str(start_time),  # Start time
                '-i', download_url,      # Input URL
                '-t', str(duration),     # Duration
                '-c', 'copy',            # Copy streams (no re-encoding)
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                str(local_output_path),
                '-y'  # Overwrite output
            ]
            
            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0 or not local_output_path.exists():
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"❌ Segment {segment_index+1} download failed: {error_msg}")
                raise Exception(f"FFmpeg failed: {error_msg}")
            
            # Get file info
            file_size = local_output_path.stat().st_size
            file_size_mb = file_size / (1024*1024)
            logger.info(f"✅ Segment {segment_index+1} downloaded: {file_size_mb:.1f} MB")
            
            # Upload to Azure temp storage (user requirement #3)
            azure_temp_url = None
            if self.azure_storage:
                try:
                    logger.info(f"☁️ Uploading segment {segment_index+1} to Azure temp storage...")
                    
                    # Create blob name for temp storage
                    blob_name = f"{video_id}/segments/{safe_title}_{segment_index+1}.mp4"
                    
                    # Upload with 2-hour expiry (temp storage)
                    azure_temp_url = await self.azure_storage.upload_file(
                        file_path=str(local_output_path),
                        blob_name=blob_name,
                        container_type="temp_videos",
                        metadata={
                            "video_id": video_id,
                            "segment_index": str(segment_index + 1),
                            "segment_title": segment_title,
                            "start_time": str(start_time),
                            "end_time": str(end_time),
                            "duration": str(duration),
                            "purpose": "segment_processing",
                            "workflow_step": "downloaded_segment"
                        }
                    )
                    
                    logger.info(f"✅ Segment {segment_index+1} uploaded to Azure temp storage")
                    
                except Exception as azure_error:
                    logger.warning(f"⚠️ Azure temp upload failed for segment {segment_index+1}: {azure_error}")
                    # Continue without Azure - local file still available
            
            return {
                "success": True,
                "segment_index": segment_index + 1,
                "segment_title": segment_title,
                "local_path": str(local_output_path),
                "azure_temp_url": azure_temp_url,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "file_size": file_size,
                "file_size_mb": round(file_size_mb, 1),
                "storage_location": "azure_temp" if azure_temp_url else "local_only"
            }
                
        except Exception as e:
            logger.error(f"Segment download/upload error: {str(e)}")
            return {
                "success": False,
                "segment_index": segment_index + 1,
                "error": str(e)
            }
    
    # Keep the original download method for backward compatibility
    async def download_video_segments(
        self, 
        youtube_url: str, 
        viral_segments: List[Dict[str, Any]], 
        quality: str = "1080p"
    ) -> List[Path]:
        """
        Original method for backward compatibility - downloads segments to local storage only
        """
        try:
            logger.info(f"🎯 Starting segment download (local only) for {len(viral_segments)} segments")
            
            # Get download URL from Apify
            download_url = await self._get_video_download_url(youtube_url, quality)
            
            # Download segments in parallel
            segment_tasks = []
            for i, segment in enumerate(viral_segments):
                task = self._download_single_segment(
                    download_url=download_url,
                    segment_index=i,
                    start_time=segment['start'],
                    end_time=segment['end'],
                    segment_title=segment.get('title', f'segment_{i+1}'),
                    quality=quality
                )
                segment_tasks.append(task)
            
            # Wait for all segments to download (using batch processing)
            segment_paths = await self._process_path_downloads_in_batches(segment_tasks, batch_size=3)
            
            # Filter out failed downloads
            successful_downloads = [
                path for path in segment_paths 
                if isinstance(path, Path) and path.exists()
            ]
            
            logger.info(f"✅ Successfully downloaded {len(successful_downloads)}/{len(viral_segments)} segments")
            return successful_downloads
            
        except Exception as e:
            logger.error(f"Segment download failed: {str(e)}")
            raise
    
    async def _get_video_download_url(self, youtube_url: str, quality: str) -> str:
        """
        Use Apify to get the video download URL without downloading the full file
        """
        logger.info("🔍 Getting download URL from Apify...")
        
        # Map quality to Apify resolution
        quality_map = {
            "8k": "2160p", "4k": "2160p", "1440p": "1440p", 
            "1080p": "1080p", "720p": "720p", "best": "1080p"
        }
        apify_quality = quality_map.get(quality, "1080p")
        
        run_input = {
            "urls": [youtube_url],
            "resolution": apify_quality,
            "max_concurrent": 1
        }
        
        # Run Apify Actor
        run = self.client.actor("xtech/youtube-video-downloader").call(run_input=run_input)
        
        # Get results
        dataset = self.client.dataset(run["defaultDatasetId"])
        results = dataset.list_items().items
        
        if not results or len(results) == 0:
            raise Exception("No download results returned from Apify")
        
        video_data = results[0]
        download_url = video_data.get('download_url')
        
        if not download_url:
            raise Exception("No download URL provided by Apify")
        
        logger.info(f"✅ Got download URL from Apify")
        return download_url
    
    async def _download_single_segment(
        self,
        download_url: str,
        segment_index: int,
        start_time: float,
        end_time: float,
        segment_title: str,
        quality: str
    ) -> Path:
        """
        Download a single segment using FFmpeg with HTTP range requests
        """
        try:
            # Sanitize filename using proper Unicode handling (same as above)
            import unicodedata
            import re
            
            # Convert Unicode characters (like Cyrillic) to ASCII equivalents
            try:
                safe_title = unicodedata.normalize('NFKD', segment_title)
                safe_title = safe_title.encode('ascii', 'ignore').decode('ascii')
            except Exception:
                # Fallback: remove non-ASCII characters
                safe_title = ''.join(char for char in segment_title if ord(char) < 128)
            
            # Keep only safe characters and replace spaces
            safe_title = re.sub(r'[^a-zA-Z0-9\-_]', '_', safe_title).strip('_')
            safe_title = re.sub(r'[_]+', '_', safe_title)  # Multiple underscores -> single
            
            # Ensure it's not empty
            if not safe_title:
                safe_title = f"segment_{segment_index+1}"
            
            # Limit length for filesystem compatibility
            if len(safe_title) > 100:
                safe_title = safe_title[:100].rstrip('_')
            
            duration = end_time - start_time
            output_path = self.local_downloads_dir / f"{safe_title}_{segment_index+1}_{quality}.mp4"
            
            logger.info(f"📥 Downloading segment {segment_index+1}: {safe_title} ({start_time:.1f}s-{end_time:.1f}s)")
            logger.info(f"📝 Original title: '{segment_title}' → Safe title: '{safe_title}'")
            
            # FFmpeg command to download specific segment
            cmd = [
                'ffmpeg',
                '-hide_banner', '-loglevel', 'error',
                '-ss', str(start_time),  # Start time
                '-i', download_url,      # Input URL
                '-t', str(duration),     # Duration
                '-c', 'copy',            # Copy streams (no re-encoding)
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                str(output_path),
                '-y'  # Overwrite output
            ]
            
            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024*1024)
                logger.info(f"✅ Segment {segment_index+1} downloaded: {file_size_mb:.1f} MB")
                return output_path
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"❌ Segment {segment_index+1} download failed: {error_msg}")
                raise Exception(f"FFmpeg failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Segment download error: {str(e)}")
            raise
    
    async def _process_downloads_in_batches(self, download_tasks: List, batch_size: int = 3) -> List:
        """
        Process download tasks in batches to avoid overwhelming APIs
        
        Args:
            download_tasks: List of download tasks to process
            batch_size: Number of downloads to process simultaneously
            
        Returns:
            List of results from all download tasks
        """
        total_downloads = len(download_tasks)
        all_results = []
        
        logger.info(f"📥 Processing {total_downloads} downloads in batches of {batch_size}")
        
        # Process in batches
        for batch_start in range(0, total_downloads, batch_size):
            batch_end = min(batch_start + batch_size, total_downloads)
            batch_number = (batch_start // batch_size) + 1
            total_batches = (total_downloads + batch_size - 1) // batch_size  # Ceiling division
            
            current_batch = download_tasks[batch_start:batch_end]
            batch_size_actual = len(current_batch)
            
            logger.info(f"📥 Download batch {batch_number}/{total_batches}: segments {batch_start+1}-{batch_end} ({batch_size_actual} downloads)")
            
            # Process current batch in parallel
            try:
                batch_start_time = time.time()
                batch_results = await asyncio.gather(*current_batch, return_exceptions=True)
                batch_duration = time.time() - batch_start_time
                
                logger.info(f"✅ Download batch {batch_number} completed in {batch_duration:.1f}s")
                
                # Count successful vs failed in this batch
                batch_successful = sum(1 for r in batch_results 
                                     if not isinstance(r, Exception) and 
                                        isinstance(r, dict) and r.get("success"))
                batch_failed = batch_size_actual - batch_successful
                
                logger.info(f"   📊 Download batch {batch_number} results: {batch_successful} successful, {batch_failed} failed")
                
                all_results.extend(batch_results)
                
            except Exception as e:
                logger.error(f"❌ Download batch {batch_number} failed: {str(e)}")
                # Add error results for this batch
                error_results = [{"success": False, "error": f"Download batch failed: {str(e)}"} 
                               for _ in current_batch]
                all_results.extend(error_results)
            
            # Small delay between download batches to be API-friendly
            if batch_number < total_batches:
                logger.info(f"⏸️ Brief pause before next download batch...")
                await asyncio.sleep(1)  # 1-second pause between download batches
        
        final_successful = sum(1 for r in all_results 
                              if not isinstance(r, Exception) and 
                                 isinstance(r, dict) and r.get("success"))
        final_failed = total_downloads - final_successful
        
        logger.info(f"🎉 Download batch processing completed: {final_successful} successful, {final_failed} failed")
        
        return all_results

    async def _process_path_downloads_in_batches(self, download_tasks: List, batch_size: int = 3) -> List:
        """
        Process download tasks in batches for the original download method (returns Path objects)
        
        Args:
            download_tasks: List of download tasks to process
            batch_size: Number of downloads to process simultaneously
            
        Returns:
            List of results (Path objects for success, Exceptions for failures)
        """
        total_downloads = len(download_tasks)
        all_results = []
        
        logger.info(f"📥 Processing {total_downloads} path downloads in batches of {batch_size}")
        
        # Process in batches
        for batch_start in range(0, total_downloads, batch_size):
            batch_end = min(batch_start + batch_size, total_downloads)
            batch_number = (batch_start // batch_size) + 1
            total_batches = (total_downloads + batch_size - 1) // batch_size
            
            current_batch = download_tasks[batch_start:batch_end]
            
            logger.info(f"📥 Path download batch {batch_number}/{total_batches}: segments {batch_start+1}-{batch_end}")
            
            try:
                batch_results = await asyncio.gather(*current_batch, return_exceptions=True)
                all_results.extend(batch_results)
                
                # Count successful paths
                successful_paths = sum(1 for r in batch_results if isinstance(r, Path) and r.exists())
                logger.info(f"✅ Path download batch {batch_number} completed: {successful_paths} successful")
                
            except Exception as e:
                logger.error(f"❌ Path download batch {batch_number} failed: {str(e)}")
                all_results.extend([e] * len(current_batch))
            
            # Brief pause between batches
            if batch_number < total_batches:
                await asyncio.sleep(1)
        
        successful_total = sum(1 for r in all_results if isinstance(r, Path) and r.exists())
        logger.info(f"🎉 Path download batching completed: {successful_total} successful paths")
        
        return all_results

    def estimate_bandwidth_savings(self, viral_segments: List[Dict], video_duration: float) -> Dict[str, Any]:
        """
        Calculate estimated bandwidth savings from segment-based downloading
        """
        total_segment_duration = sum(segment['end'] - segment['start'] for segment in viral_segments)
        
        # Handle cases where video_duration is None or 0
        if not video_duration or video_duration <= 0:
            # Fallback: estimate video duration from the maximum end time in segments
            if viral_segments:
                estimated_duration = max(segment.get('end', 0) for segment in viral_segments)
                if estimated_duration > 0:
                    video_duration = estimated_duration
                else:
                    # If we still can't get duration, assume segments cover 50% of total video
                    video_duration = total_segment_duration * 2
            else:
                # No segments to estimate from, use total segment duration
                video_duration = total_segment_duration
            
            print(f"⚠️  Video duration was None/0, estimated as {video_duration:.1f}s from segments")
        
        # Ensure we don't divide by zero
        if video_duration <= 0:
            video_duration = 1.0  # Minimum fallback
        
        savings_percentage = ((video_duration - total_segment_duration) / video_duration) * 100
        
        return {
            "total_video_duration": video_duration,
            "total_segment_duration": total_segment_duration,
            "bandwidth_savings_percentage": round(max(0, savings_percentage), 1),  # Ensure non-negative
            "time_savings_estimate": round(max(0, video_duration - total_segment_duration), 1)
        }

# Global service instance
segment_download_service = SegmentDownloadService()

async def get_segment_download_service() -> SegmentDownloadService:
    """Get the global segment download service instance"""
    return segment_download_service 