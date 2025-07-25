#!/usr/bin/env python3
"""
HuntAPI service for YouTube video downloading as a fallback for Apify
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class HuntAPIError(Exception):
    """Custom exception for HuntAPI errors"""
    pass

class HuntAPIService:
    """
    HuntAPI service for downloading YouTube videos
    Used as a fallback when Apify actor fails
    """
    
    def __init__(self):
        self.api_key = os.getenv("HUNTAPI_TOKEN") 
        if not self.api_key:
            raise ValueError("HUNTAPI_TOKEN or HUNTAPI_KEY environment variable not set")
        
        self.base_url = "https://huntapi.com/api/v1"
        self.headers = {"x-api-key": self.api_key}
        
        # Polling configuration
        self.max_poll_time = 3600  # 1 hour max (as per docs)
        self.poll_interval = 30    # 30 seconds between polls
        
    async def download_video(self, url: str, quality: str = "best") -> str:
        """
        Download YouTube video and return the download URL
        
        Args:
            url: YouTube video URL
            quality: Video quality (best, 1080p, 720p, etc.)
            
        Returns:
            Direct download URL to the MP4 file
            
        Raises:
            HuntAPIError: If download fails
        """
        try:
            logger.info(f"🔄 Starting HuntAPI download: {url} (quality: {quality})")
            
            # Step 1: Create download job
            job_id = await self._create_download_job(url, quality)
            logger.info(f"📋 HuntAPI job created: {job_id}")
            
            # Step 2: Poll for completion
            download_url = await self._poll_job_completion(job_id)
            logger.info(f"✅ HuntAPI download complete: {download_url}")
            
            return download_url
            
        except Exception as e:
            logger.error(f"HuntAPI download failed: {str(e)}")
            raise HuntAPIError(f"HuntAPI download failed: {str(e)}")
    
    async def _create_download_job(self, url: str, quality: str) -> str:
        """
        Create a download job and return job ID
        """
        # Map quality to HuntAPI format
        quality_map = {
            "8k": "best",    # HuntAPI doesn't specify 8k, use best
            "4k": "best",    # HuntAPI doesn't specify 4k, use best  
            "1440p": "best", # HuntAPI doesn't specify 1440p, use best
            "1080p": "1080p",
            "720p": "720p", 
            "480p": "480p",
            "360p": "360p",
            "best": "best"
        }
        huntapi_quality = quality_map.get(quality, "best")
        
        params = {
            "query": url,
            "video_quality": huntapi_quality,
            "download_type": "audio_video",
            "video_format": "mp4"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/video/download",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            job_id = data.get("job_id")
            
            if not job_id:
                raise HuntAPIError("No job_id returned from HuntAPI")
                
            return job_id
            
        except requests.RequestException as e:
            raise HuntAPIError(f"Failed to create HuntAPI job: {str(e)}")
        except Exception as e:
            raise HuntAPIError(f"Unexpected error creating HuntAPI job: {str(e)}")
    
    async def _poll_job_completion(self, job_id: str) -> str:
        """
        Poll job status until completion and return download URL
        """
        start_time = time.time()
        
        while time.time() - start_time < self.max_poll_time:
            try:
                response = requests.get(
                    f"{self.base_url}/jobs/{job_id}",
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                status = data.get("status")
                
                logger.info(f"📊 HuntAPI job {job_id} status: {status}")
                
                if status == "CompletedJob":
                    result = data.get("result", {})
                    download_url = result.get("response")
                    
                    if not download_url:
                        raise HuntAPIError("No download URL in completed job result")
                    
                    return download_url
                
                elif status == "Error":
                    error_msg = data.get("error", "Unknown error")
                    raise HuntAPIError(f"HuntAPI job failed: {error_msg}")
                
                elif status == "QueuedJob":
                    # Job still processing, wait and poll again
                    logger.info(f"⏳ HuntAPI job {job_id} still processing, waiting {self.poll_interval}s...")
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                else:
                    # Unknown status, treat as still processing
                    logger.warning(f"⚠️ Unknown HuntAPI job status: {status}, continuing to poll...")
                    await asyncio.sleep(self.poll_interval)
                    continue
                    
            except requests.RequestException as e:
                logger.warning(f"⚠️ Error polling HuntAPI job {job_id}: {str(e)}, retrying...")
                await asyncio.sleep(self.poll_interval)
                continue
            except Exception as e:
                raise HuntAPIError(f"Unexpected error polling job {job_id}: {str(e)}")
        
        # Timeout reached
        raise HuntAPIError(f"HuntAPI job {job_id} timed out after {self.max_poll_time} seconds")
    
    def get_video_metadata(self, job_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract video metadata from HuntAPI job result
        """
        metadata = job_result.get("result", {}).get("metadata", {})
        
        return {
            "title": metadata.get("title", "Unknown Video"),
            "duration": metadata.get("duration"),
            "resolution": metadata.get("resolution"),
            "format": metadata.get("format", "mp4")
        } 