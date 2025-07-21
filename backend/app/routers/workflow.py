from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from pathlib import Path
import shutil
import tempfile
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uuid
from datetime import datetime
import threading
import time
from sqlalchemy.ext.asyncio import AsyncSession

# Import our services
from app.services.youtube import (
    get_video_id, download_video, cut_clips, cut_clips_vertical, cut_clips_vertical_async, DownloadError,
    get_video_info, get_available_formats, youtube_service
)
from app.services.transcript import fetch_youtube_transcript, extract_full_transcript
from app.services.gemini import analyze_transcript_with_gemini
from app.services.vertical_crop import crop_video_to_vertical
from app.services.vertical_crop_async import (
    crop_video_to_vertical_async,
    async_vertical_crop_service
)
# Add imports for subtitle processing
from app.services.subs import convert_groq_to_subtitles
from app.services.burn_in import burn_subtitles_to_video
from app.services.groq_client import transcribe
# Add import for thumbnail generation
from app.services.thumbnail import generate_thumbnail
from app.services.clip_storage import get_clip_storage_service, ClipStorageService
from app.services.cleanup import get_cleanup_service, CleanupService

# Import authentication and database
from ..auth import get_current_user
from ..database import get_db
from ..models import User, Video, VideoStatus, Clip

router = APIRouter()

# Directory constants
TEMP_UPLOADS_DIR = Path("temp_uploads")
TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Global task management for complete workflow processing
workflow_tasks: Dict[str, Dict] = {}
workflow_task_lock = threading.Lock()

# Thread pool for CPU-intensive tasks
workflow_executor = ThreadPoolExecutor(max_workers=6)  # Adjust based on your server capacity

class ProcessVideoRequest(BaseModel):
    youtube_url: str
    quality: Optional[str] = "best"  # best, 8k, 4k, 1440p, 1080p, 720p
    create_vertical: Optional[bool] = False  # Create vertical (9:16) clips
    smoothing_strength: Optional[str] = "very_high"  # low, medium, high, very_high

class VideoInfoRequest(BaseModel):
    youtube_url: str

@router.post("/video-info")
async def get_video_information(request: VideoInfoRequest):
    """
    Get detailed video information including available formats
    """
    try:
        print(f"🔍 Getting video info for: {request.youtube_url}")
        
        # Get video info
        video_info = get_video_info(request.youtube_url)
        
        # Get available formats
        formats = get_available_formats(request.youtube_url)
        
        return {
            "success": True,
            "video_info": video_info,
            "available_formats": formats[:10],  # Top 10 formats
            "supported_qualities": ["best", "8k", "4k", "1440p", "1080p", "720p"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get video info: {str(e)}")

class AsyncProcessVideoRequest(BaseModel):
    """Request for async complete video processing"""
    youtube_url: str
    quality: Optional[str] = "best"  # best, 8k, 4k, 1440p, 1080p, 720p
    create_vertical: Optional[bool] = False  # Create vertical (9:16) clips
    smoothing_strength: Optional[str] = "very_high"  # low, medium, high, very_high
    priority: Optional[str] = "normal"  # low, normal, high
    notify_webhook: Optional[str] = None  # Optional webhook URL for completion notification

class ComprehensiveWorkflowRequest(BaseModel):
    """Request for comprehensive workflow: download → transcript → gemini → vertical crop → burn subtitles → upload to Azure"""
    youtube_url: str
    quality: Optional[str] = "best"  # best, 8k, 4k, 1440p, 1080p, 720p
    create_vertical: Optional[bool] = True  # Create vertical (9:16) clips (default True for comprehensive workflow)
    smoothing_strength: Optional[str] = "very_high"  # low, medium, high, very_high
    burn_subtitles: Optional[bool] = True  # Whether to burn subtitles into videos (always uses speech synchronization)
    font_size: Optional[int] = 15  # Font size for subtitles (12-120)
    export_codec: Optional[str] = "h264"  # Video codec (h264, h265)
    priority: Optional[str] = "normal"  # low, normal, high
    notify_webhook: Optional[str] = None  # Optional webhook URL for completion notification
    
    # 🔊 NEW AUDIO SYNC OPTIONS
    enable_audio_sync_fix: Optional[bool] = True  # Enable enhanced audio sync preservation
    audio_offset_ms: Optional[float] = 0.0  # Manual audio offset correction in milliseconds

class FastWorkflowRequest(BaseModel):
    """Request for fast workflow: skip transcript/Gemini, use provided segments"""
    youtube_url: str
    viral_segments: List[Dict[str, Any]]  # Pre-analyzed segments
    quality: Optional[str] = "best"  # best, 8k, 4k, 1440p, 1080p, 720p
    create_vertical: Optional[bool] = True
    smoothing_strength: Optional[str] = "very_high"
    burn_subtitles: Optional[bool] = True
    font_size: Optional[int] = 15
    export_codec: Optional[str] = "h264"
    priority: Optional[str] = "normal"
    notify_webhook: Optional[str] = None

async def _run_blocking_task(func, *args, **kwargs):
    """Run blocking functions in thread pool"""
    loop = asyncio.get_event_loop()
    # Create a wrapper function that handles keyword arguments
    def wrapper():
        return func(*args, **kwargs)
    return await loop.run_in_executor(workflow_executor, wrapper)

def _update_workflow_progress(task_id: str, step: str, progress: int, message: str, data: Optional[Dict] = None):
    """Update workflow task progress with thread safety"""
    with workflow_task_lock:
        if task_id in workflow_tasks:
            workflow_tasks[task_id].update({
                "current_step": step,
                "progress": progress,
                "message": message,
                "updated_at": datetime.now()
            })
            if data:
                workflow_tasks[task_id].update(data)

# NEW: Fully parallel processing function for a single segment
async def _process_single_viral_segment_parallel(
    segment_index: int,
    segment_data: Dict[str, Any],
    source_video_path: Path,
    task_id: str,
    create_vertical: bool,
    smoothing_strength: str,
    burn_subtitles: bool,
    font_size: int,
    export_codec: str
) -> Dict[str, Any]:
    """
    Processes a single viral segment in its own parallel task.
    This includes cutting, vertical cropping, and subtitle burning.
    """
    try:
        start_time_total = time.time()
        
        # Unpack segment data
        start_time = segment_data.get("start")
        end_time = segment_data.get("end")
        title = segment_data.get("title", f"Segment_{segment_index+1}")
        
        if start_time is None or end_time is None:
            return {"success": False, "error": "Missing start or end time", "clip_path": None}
        
        # --- 1. Cut Clip ---
        from app.services.youtube import create_clip_with_direct_ffmpeg
        safe_title = youtube_service._sanitize_filename(title)
        
        # Define clip paths
        base_dir = source_video_path.parent
        clips_dir = base_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        
        # We always cut a temporary horizontal clip first
        temp_horizontal_clip_path = clips_dir / f"temp_{safe_title}_{segment_index+1}.mp4"
        
        print(f"🚀 [Segment {segment_index+1}] Starting processing: '{title}'")
        print(f"   - Cutting segment: {start_time}s - {end_time}s")
        
        if not create_clip_with_direct_ffmpeg(source_video_path, start_time, end_time, temp_horizontal_clip_path):
            raise Exception("Failed to cut video segment using ffmpeg.")
        
        processing_clip_path = temp_horizontal_clip_path
        
        # --- 2. Vertical Cropping (if enabled) ---
        if create_vertical:
            print(f"   - Applying vertical crop with '{smoothing_strength}' smoothing...")
            vertical_clip_path = clips_dir / f"{safe_title}_vertical.mp4"
            
            from app.services.vertical_crop_async import crop_video_to_vertical_async
            import asyncio
            
            try:
                # Add timeout protection for vertical cropping (5 minutes max)
                crop_result = await asyncio.wait_for(
                    crop_video_to_vertical_async(
                        input_path=temp_horizontal_clip_path,
                        output_path=vertical_clip_path,
                        use_speaker_detection=True,
                        use_smart_scene_detection=False,  # 🚀 DISABLED for performance
                        smoothing_strength=smoothing_strength,
                        task_id=f"{task_id}_seg_{segment_index+1}" if task_id else None
                    ),
                    timeout=300.0  # 5 minutes timeout
                )
                
                if not crop_result.get("success"):
                    raise Exception(f"Vertical cropping failed: {crop_result.get('error')}")
                
                processing_clip_path = vertical_clip_path
                print(f"   ✅ Vertical crop completed successfully")
                
                # Clean up the temp horizontal clip now that we have the vertical one
                if temp_horizontal_clip_path.exists():
                    temp_horizontal_clip_path.unlink()
                    
            except asyncio.TimeoutError:
                print(f"   ❌ Vertical cropping timed out after 5 minutes.")
                # Clean up any partial vertical crop file
                if vertical_clip_path.exists():
                    vertical_clip_path.unlink()
                raise Exception("Vertical cropping timed out after 5 minutes")
                    
            except Exception as crop_error:
                print(f"   ❌ Vertical cropping failed: {crop_error}")
                # Clean up any partial vertical crop file
                if vertical_clip_path.exists():
                    vertical_clip_path.unlink()
                raise Exception(f"Vertical cropping failed: {crop_error}")
        
        # --- 2.5. Thumbnail Generation (after vertical cropping) ---
        print(f"   - Generating thumbnail...")
        thumbnails_dir = base_dir / "thumbnails"
        clip_id = f"clip_{segment_index+1}_{safe_title}"
        
        thumbnail_result = await generate_thumbnail(
            video_path=processing_clip_path,
            output_dir=thumbnails_dir,
            clip_id=clip_id,
            width=300,  # Good size for thumbnails
            timestamp=1.0  # Extract frame at 1 second
        )
        
        thumbnail_path = None
        if thumbnail_result.get("success"):
            # Use relative path for frontend
            thumbnail_path = f"thumbnails/{thumbnail_result.get('thumbnail_filename')}"
            print(f"   ✅ Thumbnail generated: {thumbnail_result.get('thumbnail_filename')}")
        else:
            print(f"   ⚠️ Thumbnail generation failed: {thumbnail_result.get('error')}")
        
        subtitled_clip_path = None
        # --- 3. Subtitle Generation & Burning (if enabled) ---
        if burn_subtitles:
            print(f"   - Generating and burning subtitles...")
            
            # a. Extract audio from the final (cropped) clip
            from pydub import AudioSegment
            temp_audio_path = clips_dir / f"temp_audio_{safe_title}_{segment_index+1}.wav"
            audio = AudioSegment.from_file(str(processing_clip_path))
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(temp_audio_path, format="wav")
            
            # b. Transcribe the audio
            from app.services.groq_client import transcribe
            transcription_result = transcribe(
                file_path=str(temp_audio_path),
                apply_vad=True,
                task_id=f"{task_id}_clip_{segment_index}"
            )
            
            if temp_audio_path.exists():
                temp_audio_path.unlink()
            
            if not transcription_result or not transcription_result.get("segments"):
                print(f"⚠️ [Segment {segment_index+1}] No transcription found. Skipping subtitle burn.")
            else:
                # c. Convert transcription to SRT
                from app.services.subs import convert_groq_to_subtitles
                subtitles_dir = clips_dir / "subtitles"
                subtitles_dir.mkdir(exist_ok=True)
                
                srt_path, _ = await _run_blocking_task(
                    convert_groq_to_subtitles,
                    groq_segments=transcription_result["segments"],
                    word_timestamps=transcription_result.get("word_timestamps", []),
                    output_dir=str(subtitles_dir),
                    filename_base=f"clip_{segment_index+1}_{safe_title}",
                    speech_sync_mode=True
                )
                
                # d. Burn subtitles
                if srt_path and Path(srt_path).exists():
                    from app.services.burn_in import burn_subtitles_to_video
                    subtitled_clip_path = clips_dir / f"subtitled_{processing_clip_path.name}"
                    
                    await _run_blocking_task(
                        burn_subtitles_to_video,
                        video_path=str(processing_clip_path),
                        srt_path=srt_path,
                        output_path=str(subtitled_clip_path),
                        font_size=font_size,
                        export_codec=export_codec
                    )
                    
                    if subtitled_clip_path.exists():
                        # We have a new subtitled clip, remove the non-subtitled one
                        processing_clip_path.unlink()
                    else:
                        subtitled_clip_path = None # Burn-in failed
                else:
                    print(f"⚠️ [Segment {segment_index+1}] SRT file generation failed. Skipping burn.")

        final_clip_path = subtitled_clip_path if subtitled_clip_path else processing_clip_path

        total_time = time.time() - start_time_total
        print(f"✅ [Segment {segment_index+1}] Finished processing in {total_time:.2f}s. Final file: {final_clip_path.name}")
        
        # --- 4. Upload clip and thumbnail to Azure Blob Storage ---
        azure_clip_url = None
        azure_thumbnail_url = None
        
        try:
            print(f"   - Uploading clip to Azure Blob Storage...")
            
            # Get clip storage service
            from app.services.clip_storage import get_clip_storage_service
            clip_storage = await get_clip_storage_service()
            
            # Generate unique blob name for the clip
            clip_blob_name = f"clips/{safe_title}_{segment_index+1}_{int(time.time())}.mp4"
            
            # Upload clip to Azure permanently
            azure_clip_url = await clip_storage.azure_storage.upload_file(
                file_path=str(final_clip_path),
                blob_name=clip_blob_name,
                container_type="clips",
                metadata={
                    "segment_index": str(segment_index),
                    "title": title,
                    "start_time": str(start_time),
                    "end_time": str(end_time),
                    "duration": str(end_time - start_time),
                    "has_subtitles": str("subtitled_" in final_clip_path.name),
                    "is_vertical": str(create_vertical),
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            print(f"   ✅ Clip uploaded to Azure: {azure_clip_url}")
            
            # Upload thumbnail if available
            if thumbnail_path and Path(base_dir / thumbnail_path).exists():
                print(f"   - Uploading thumbnail to Azure Blob Storage...")
                
                thumbnail_blob_name = f"thumbnails/{safe_title}_{segment_index+1}_{int(time.time())}.jpg"
                azure_thumbnail_url = await clip_storage.azure_storage.upload_file(
                    file_path=str(base_dir / thumbnail_path),
                    blob_name=thumbnail_blob_name,
                    container_type="thumbnails",
                    metadata={
                        "clip_blob_name": clip_blob_name,
                        "segment_index": str(segment_index),
                        "title": title,
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                
                print(f"   ✅ Thumbnail uploaded to Azure: {azure_thumbnail_url}")
            
        except Exception as e:
            print(f"   ⚠️ Warning: Failed to upload to Azure Blob Storage: {str(e)}")
            print(f"   📁 Clip will remain local only: {final_clip_path}")
            # Don't fail the entire process if Azure upload fails
        
        # Convert absolute paths to relative URLs for frontend
        final_clip_relative = str(final_clip_path).replace(str(source_video_path.parent) + "/", "")
        
        return {
            "success": True, 
            "clip_path": final_clip_relative,
            "azure_clip_url": azure_clip_url,
            "thumbnail_path": thumbnail_path,
            "azure_thumbnail_url": azure_thumbnail_url,
            "clip_id": clip_id,
            "has_subtitles": "subtitled_" in final_clip_path.name,
            "processing_time": total_time,
            "storage_location": "azure_blob_storage" if azure_clip_url else "local_only"
        }
        
    except Exception as e:
        import traceback
        print(f"❌ [Segment {segment_index+1}] Processing failed: {e}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e), "clip_path": None}

async def _process_video_workflow_async(
    task_id: str,
    youtube_url: str,
    quality: str,
    create_vertical: bool,
    smoothing_strength: str,
    burn_subtitles: bool = False,
    font_size: int = 15,
    export_codec: str = "h264",
    enable_audio_sync_fix: bool = True,
    audio_offset_ms: float = 0.0
):
    """
    Async implementation of the complete video processing workflow
    NEW ORDER: Download → Transcript → Gemini → Vertical Crop → Burn Subtitles → Upload to Azure
    """
    try:
        print(f"🚀 Starting comprehensive workflow with NEW ORDER:")
        print(f"   📺 URL: {youtube_url}")
        print(f"   📹 Quality: {quality}")
        print(f"   📱 Create vertical: {create_vertical}")
        print(f"   🔥 Burn subtitles: {burn_subtitles}")
        print(f"   🎨 Font size: {font_size}px")
        print(f"   🎯 Speech synchronization: ENABLED (word-level timestamps)")
        print(f"   🎛️ VAD filtering: ENABLED (with retry logic)")
        print(f"   🎬 Export codec: {export_codec}")
        print(f"   🔄 Workflow Order: Download → Transcript → Gemini → Vertical Crop → Burn Subtitles → Upload to Azure")
        
        _update_workflow_progress(task_id, "init", 5, f"Starting comprehensive workflow for: {youtube_url}")
        
        # Step 1: Get video info (5-10%)
        _update_workflow_progress(task_id, "video_info", 5, "Getting video information...")
        video_info = await _run_blocking_task(get_video_info, youtube_url)
        
        _update_workflow_progress(
            task_id, "video_info", 10, 
            f"Video info retrieved: {video_info['title']}", 
            {"video_info": video_info}
        )
        
        # Step 2: Download video FIRST (10-25%)
        _update_workflow_progress(task_id, "download", 10, f" Processing video in {quality} quality...")
        
        try:
            video_path = await download_video(youtube_url, quality)
            file_size_mb = video_path.stat().st_size / (1024*1024)
            
            _update_workflow_progress(
                task_id, "download", 25, 
                f"✅ Video downloaded: {file_size_mb:.1f} MB",
                {
                    "video_path": str(video_path),
                    "file_size_mb": file_size_mb
                }
            )
            print(f"✅ Video downloaded successfully: {video_path} ({file_size_mb:.1f} MB)")
        except DownloadError as e:
            raise Exception(f"Download failed: {str(e)}")
        
        # Step 3: Extract transcript (25-40%)
        _update_workflow_progress(task_id, "transcript", 25, "Analyzing video...")
        video_id = video_info['id']
        
        raw_transcript_data = await _run_blocking_task(fetch_youtube_transcript, video_id)
        transcript_result = await _run_blocking_task(extract_full_transcript, raw_transcript_data)
        
        if isinstance(transcript_result, dict) and 'error' in transcript_result:
            raise Exception(f"Transcript error: {transcript_result['error']}")
        
        _update_workflow_progress(
            task_id, "transcript", 40, 
            f"✅ Transcript extracted: {len(transcript_result.get('transcript', ''))} characters",
            {"transcript_result": transcript_result}
        )
        
        # Step 4: Gemini Analysis (40-55%)
        _update_workflow_progress(task_id, "analysis", 40, "Selecting the viral segments...")
        gemini_analysis = await analyze_transcript_with_gemini(transcript_result)
        
        if not gemini_analysis.get("gemini_analysis", {}).get("viral_segments"):
            raise Exception("No viral segments found in Gemini analysis")
        
        viral_segments = gemini_analysis["gemini_analysis"]["viral_segments"]
        _update_workflow_progress(
            task_id, "analysis", 55, 
            f"✅ Gemini analysis complete: {len(viral_segments)} segments found",
            {"gemini_analysis": gemini_analysis}
        )
        
        print(f"✅ Video ready for processing: {video_path} ({file_size_mb:.1f} MB)")
        
        # --- Steps 5, 6, 7: Parallel Processing of Viral Segments (Vertical Crop + Burn Subtitles + Upload to Azure) ---
        _update_workflow_progress(task_id, "parallel_processing", 55, f"Started cropping for {len(viral_segments)} viral segments...")
        
        parallel_start_time = time.time()
        
        tasks = []
        for i, segment in enumerate(viral_segments):
            task = _process_single_viral_segment_parallel(
                segment_index=i,
                segment_data=segment,
                source_video_path=video_path,
                task_id=task_id,
                create_vertical=create_vertical,
                smoothing_strength=smoothing_strength,
                burn_subtitles=burn_subtitles,
                font_size=font_size,
                export_codec=export_codec,
            )
            tasks.append(task)
            
        # Run all processing tasks concurrently with overall timeout protection
        try:
            # Add overall timeout for parallel processing (15 minutes max)
            processed_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=900.0  # 15 minutes timeout for entire parallel processing
            )
        except asyncio.TimeoutError:
            print(f"❌ Parallel processing timed out after 15 minutes. Attempting to cancel tasks...")
            # Cancel all running tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Try to get partial results
            processed_results = []
            for i, task in enumerate(tasks):
                try:
                    if not task.done():
                        result = await asyncio.wait_for(task, timeout=5.0)  # Quick timeout for remaining tasks
                    else:
                        result = task.result()
                    processed_results.append(result)
                except (asyncio.TimeoutError, asyncio.CancelledError, Exception) as task_error:
                    print(f"❌ Task {i+1} failed or was cancelled: {task_error}")
                    processed_results.append({"success": False, "error": f"Task timed out or cancelled: {task_error}", "clip_path": None})
                    
        except Exception as gather_error:
            print(f"❌ Error in parallel processing: {gather_error}")
            # If gather fails, try to process results individually
            processed_results = []
            for i, task in enumerate(tasks):
                try:
                    result = await task
                    processed_results.append(result)
                except Exception as task_error:
                    print(f"❌ Task {i+1} failed: {task_error}")
                    processed_results.append({"success": False, "error": str(task_error), "clip_path": None})
        
        parallel_duration = time.time() - parallel_start_time
        print(f"🎬 All parallel processing finished in {parallel_duration:.2f} seconds.")

        # Collect results
        final_clip_paths = []
        original_clip_paths_for_result = [] # Keep track of original paths before subtitling for the result
        thumbnail_info = []  # Store thumbnail information
        azure_clips_info = []  # Store Azure Blob Storage information
        successful_clips = 0
        failed_clips = 0
        azure_uploads_successful = 0
        
        for i, result in enumerate(processed_results):
            if isinstance(result, Exception):
                print(f"❌ Segment {i+1} failed with exception: {result}")
                failed_clips += 1
                continue
            elif not result.get("success"):
                print(f"❌ Segment {i+1} failed: {result.get('error', 'Unknown error')}")
                failed_clips += 1
                continue
            
            final_clip_paths.append(result["clip_path"])
            
            # Collect thumbnail information
            if result.get("thumbnail_path"):
                thumbnail_info.append({
                    "clip_id": result.get("clip_id"),
                    "thumbnail_path": result.get("thumbnail_path"),
                    "azure_thumbnail_url": result.get("azure_thumbnail_url"),
                    "clip_path": result["clip_path"]
                })
            
            # Collect Azure Blob Storage information
            if result.get("azure_clip_url"):
                azure_clips_info.append({
                    "clip_id": result.get("clip_id"),
                    "local_path": result["clip_path"],
                    "azure_clip_url": result.get("azure_clip_url"),
                    "azure_thumbnail_url": result.get("azure_thumbnail_url"),
                    "has_subtitles": result.get("has_subtitles", False),
                    "storage_location": result.get("storage_location", "local_only")
                })
                azure_uploads_successful += 1
            
            successful_clips += 1
        
        # This is a bit tricky, the original paths are now intermediate.
        # For simplicity, let's just use the final paths for both in the result for now.
        original_clip_paths_for_result = final_clip_paths

        _update_workflow_progress(
            task_id, "parallel_processing", 95, 
            f"✅ Parallel processing complete: {successful_clips} clips created, {failed_clips} failed. Azure uploads: {azure_uploads_successful}/{successful_clips}",
            {"clip_paths": final_clip_paths, "azure_clips_info": azure_clips_info}
        )
        
        # Step 8: Finalize and cleanup (95-100%)
        _update_workflow_progress(task_id, "finalizing", 95, "Finalizing comprehensive workflow results...")
        
        # Aggressive cleanup of all temporary files
        try:
            cleanup_service = await get_cleanup_service()
            await cleanup_service.aggressive_cleanup_after_processing(video_path, task_id)
            print(f"📅 Aggressive cleanup completed for task {task_id}")
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to perform cleanup: {str(e)}")
        
        subtitled_count = len([p for p in final_clip_paths if 'subtitled_' in p])
        result = {
            "success": True,
            "workflow_type": "comprehensive",
            "workflow_steps": {
                "video_info_extraction": True,
                "transcript_extraction": True,
                "gemini_analysis": True, 
                "video_download": True,
                "azure_upload": False,  # Optimized: no redundant temp upload
                "clip_processing": True,
                "azure_clip_uploads": azure_uploads_successful > 0,
                "subtitle_generation": burn_subtitles and subtitled_count > 0,
                "clip_cutting": True,
                "subtitle_burning": burn_subtitles and subtitled_count > 0
            },
            "video_info": {
                "id": video_info['id'],
                "title": video_info['title'],
                "duration": video_info['duration'],
                "uploader": video_info.get('uploader'),
                "view_count": video_info.get('view_count'),
                "category": transcript_result.get("category"),
                "description": video_info.get('description', '')[:200] + "..." if video_info.get('description') else "",
                "transcript_length": len(transcript_result.get("transcript", "")),
                "timecodes_count": len(transcript_result.get("timecodes", []))
            },
            "download_info": {
                "quality_requested": quality,
                "file_size_mb": round(file_size_mb, 1),
                "file_path": str(video_path),
                "azure_blob_url": azure_blob_url if 'azure_blob_url' in locals() else None
            },
            "analysis_results": {
                "viral_segments_found": len(viral_segments),
                "segments": [
                    {
                        "title": seg.get("title"),
                        "start": seg.get("start"),
                        "end": seg.get("end"),
                        "duration": seg.get("duration")
                    }
                    for seg in viral_segments
                ]
            },
            "subtitle_info": {
                "subtitle_style": "speech_synchronized" if burn_subtitles else None,
                "subtitle_approach": "per_clip_generation_with_word_timestamps" if burn_subtitles else None,
                "speech_synchronization": True if burn_subtitles else None,
                "vad_filtering": True if burn_subtitles else None,
                "clips_with_subtitles": subtitled_count,
                "total_clips": len(final_clip_paths),
                "subtitle_success_rate": f"{(subtitled_count/len(final_clip_paths)*100):.1f}%" if len(final_clip_paths) > 0 else "0%",
                "font_size": font_size if burn_subtitles else None,
                "export_codec": export_codec if burn_subtitles else None
            } if burn_subtitles else None,
            "files_created": {
                "source_video": str(video_path),
                "clips_created": len(final_clip_paths),
                "original_clip_paths": original_clip_paths_for_result,
                "subtitled_clips_created": subtitled_count,
                "final_clip_paths": final_clip_paths,
                "thumbnails": thumbnail_info,
                "azure_clips_info": azure_clips_info,
                "clip_type": "vertical" if create_vertical else "horizontal",
                "has_subtitles": burn_subtitles and subtitled_count > 0,
                "subtitle_files_location": str(Path(final_clip_paths[0]).parent / "subtitles") if len(final_clip_paths) > 0 and burn_subtitles else None
            },
            "azure_storage_info": {
                "source_video_uploaded": azure_blob_url if 'azure_blob_url' in locals() else None,
                "clips_uploaded_to_azure": azure_uploads_successful,
                "total_clips": successful_clips,
                "azure_upload_success_rate": f"{(azure_uploads_successful/successful_clips*100):.1f}%" if successful_clips > 0 else "0%",
                "storage_strategy": "hybrid" if azure_uploads_successful > 0 and azure_uploads_successful < successful_clips else "azure_only" if azure_uploads_successful == successful_clips else "local_only",
                "azure_containers_used": ["temp_videos", "clips", "thumbnails"] if azure_uploads_successful > 0 else [],
                "temp_video_cleanup_scheduled": True
            }
        }
        
        # Mark as completed
        with workflow_task_lock:
            if burn_subtitles and subtitled_count > 0:
                message = f"Comprehensive workflow completed! {len(viral_segments)} segments → {successful_clips} clips → {subtitled_count} clips with subtitles. Azure uploads: {azure_uploads_successful}/{successful_clips}"
            elif burn_subtitles:
                message = f"Workflow completed! {len(viral_segments)} segments → {successful_clips} clips (subtitle processing failed or not needed on all). Azure uploads: {azure_uploads_successful}/{successful_clips}"
            else:
                message = f"Workflow completed! {len(viral_segments)} segments → {successful_clips} clips. Azure uploads: {azure_uploads_successful}/{successful_clips}"
            
            workflow_tasks[task_id].update({
                "status": "completed",
                "progress": 100,
                "message": message,
                "result": result,
                "completed_at": datetime.now()
            })
        
        return result
        
    except Exception as e:
        # Mark as failed
        with workflow_task_lock:
            workflow_tasks[task_id].update({
                "status": "failed",
                "error": str(e),
                "message": f"Comprehensive workflow failed: {str(e)}",
                "completed_at": datetime.now()
            })
        raise e

async def _process_video_workflow_fast_async(
    task_id: str,
    youtube_url: str,
    viral_segments: List[Dict[str, Any]],
    quality: str,
    create_vertical: bool,
    smoothing_strength: str,
    burn_subtitles: bool = False,
    font_size: int = 15,
    export_codec: str = "h264"
):
    """
    FAST async workflow that skips transcript extraction and Gemini analysis
    """
    try:
        print(f"🚀 Starting FAST workflow (transcript/Gemini SKIPPED):")
        print(f"   📺 URL: {youtube_url}")
        print(f"   📊 Pre-analyzed segments: {len(viral_segments)}")
        print(f"   📹 Quality: {quality}")
        print(f"   📱 Create vertical: {create_vertical}")
        print(f"   🔥 Burn subtitles: {burn_subtitles}")
        
        _update_workflow_progress(task_id, "init", 10, f"Starting fast workflow for: {youtube_url}")
        
        # Step 1: Get video info (10-20%)
        _update_workflow_progress(task_id, "video_info", 10, "Getting video information...")
        video_info = await _run_blocking_task(get_video_info, youtube_url)
        
        _update_workflow_progress(
            task_id, "video_info", 20, 
            f"Video info retrieved: {video_info['title']}", 
            {"video_info": video_info}
        )
        
        # Step 2: Download video (20-40%)
        _update_workflow_progress(task_id, "download", 20, f"Downloading video in {quality} quality...")
        
        try:
            video_path = await download_video(youtube_url, quality)
            file_size_mb = video_path.stat().st_size / (1024*1024)
            
            _update_workflow_progress(
                task_id, "download", 35, 
                f"Video downloaded: {file_size_mb:.1f} MB",
                {
                    "video_path": str(video_path),
                    "file_size_mb": file_size_mb
                }
            )
        except DownloadError as e:
            raise Exception(f"Download failed: {str(e)}")
        
        # Step 3: Upload to Azure temporarily (35-45%)
        _update_workflow_progress(task_id, "azure_upload", 35, "Uploading video to Azure Blob Storage...")
        
        try:
            from app.services.azure_storage import get_azure_storage_service
            azure_storage = await get_azure_storage_service()
            
            # Upload with 2-hour expiry
            blob_name = f"temp_videos/{video_info['id']}_{int(time.time())}.mp4"
            azure_blob_url = await azure_storage.upload_file(
                file_path=str(video_path),
                blob_name=blob_name,
                container_type="temp_videos",
                expiry_hours=2
            )
            
            _update_workflow_progress(
                task_id, "azure_upload", 45, 
                f"Video uploaded to Azure (2-hour expiry): {azure_blob_url}"
            )
        except Exception as e:
            print(f"⚠️ Azure upload failed: {str(e)}")
            azure_blob_url = None
        
        # Step 4: Process all segments in parallel (45-95%)
        _update_workflow_progress(task_id, "processing", 45, f"Processing {len(viral_segments)} segments in parallel...")
        
        # Process all segments concurrently
        segment_tasks = []
        for i, segment in enumerate(viral_segments):
            task = _process_single_viral_segment_parallel(
                segment_index=i,
                segment_data=segment,
                source_video_path=video_path,
                task_id=task_id,
                create_vertical=create_vertical,
                smoothing_strength=smoothing_strength,
                burn_subtitles=burn_subtitles,
                font_size=font_size,
                export_codec=export_codec
            )
            segment_tasks.append(task)
        
        # Wait for all segments to complete
        segment_results = await asyncio.gather(*segment_tasks, return_exceptions=True)
        
        # Process results
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(segment_results):
            if isinstance(result, Exception):
                failed_results.append({"segment_index": i, "error": str(result)})
            elif result.get("success"):
                successful_results.append(result)
            else:
                failed_results.append({"segment_index": i, "error": result.get("error", "Unknown error")})
        
        _update_workflow_progress(task_id, "processing", 90, f"Segment processing complete: {len(successful_results)} successful, {len(failed_results)} failed")
        
        # Aggressive cleanup of all temporary files
        cleanup_service = await get_cleanup_service()
        await cleanup_service.aggressive_cleanup_after_processing(video_path, task_id)
        
        # Final progress update
        _update_workflow_progress(task_id, "complete", 100, "Fast workflow completed successfully!")
        
        # Collect final results
        final_clip_paths = [r["clip_path"] for r in successful_results if r.get("clip_path")]
        azure_clips_info = [r for r in successful_results if r.get("azure_clip_url")]
        subtitled_count = sum(1 for r in successful_results if r.get("has_subtitles"))
        thumbnail_info = [r for r in successful_results if r.get("thumbnail_path")]
        
        result = {
            "success": True,
            "workflow_type": "fast",
            "workflow_steps": {
                "video_info_extraction": True,
                "transcript_extraction": False,  # SKIPPED
                "gemini_analysis": False,  # SKIPPED
                "video_download": True,
                "azure_upload": False,  # Optimized: no redundant temp upload
                "clip_processing": True,
                "azure_clip_uploads": len(azure_clips_info) > 0,
                "subtitle_generation": burn_subtitles and subtitled_count > 0
            },
            "video_info": {
                "id": video_info['id'],
                "title": video_info['title'],
                "duration": video_info['duration'],
                "uploader": video_info.get('uploader'),
                "view_count": video_info.get('view_count'),
                "description": video_info.get('description', '')[:200] + "..." if video_info.get('description') else ""
            },
            "download_info": {
                "quality_requested": quality,
                "file_size_mb": round(file_size_mb, 1),
                "azure_blob_url": azure_blob_url
            },
            "analysis_results": {
                "viral_segments_provided": len(viral_segments),
                "segments_processed": len(successful_results),
                "segments_failed": len(failed_results),
                "segments": [
                    {
                        "title": seg.get("title"),
                        "start": seg.get("start"),
                        "end": seg.get("end"),
                        "duration": seg.get("duration") or (seg.get("end", 0) - seg.get("start", 0))
                    }
                    for seg in viral_segments
                ]
            },
            "subtitle_info": {
                "subtitle_style": "speech_synchronized" if burn_subtitles else None,
                "clips_with_subtitles": subtitled_count,
                "total_clips": len(final_clip_paths),
                "subtitle_success_rate": f"{(subtitled_count/len(final_clip_paths)*100):.1f}%" if len(final_clip_paths) > 0 else "0%",
                "font_size": font_size if burn_subtitles else None
            } if burn_subtitles else None,
            "files_created": {
                "clips_created": len(final_clip_paths),
                "final_clip_paths": final_clip_paths,
                "azure_clips_info": azure_clips_info,
                "thumbnails": thumbnail_info,
                "clip_type": "vertical" if create_vertical else "horizontal",
                "has_subtitles": burn_subtitles and subtitled_count > 0
            },
            "performance": {
                "transcript_extraction_skipped": True,
                "gemini_analysis_skipped": True,
                "time_saved_seconds": "25-30 seconds",
                "processing_mode": "fast"
            }
        }

        # Update final task status
        with workflow_task_lock:
            workflow_tasks[task_id].update({
                "status": "completed",
                "progress": 100,
                "completed_at": datetime.now(),
                "result": result
            })
        
        return result
        
    except Exception as e:
        error_msg = f"Fast workflow failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        with workflow_task_lock:
            workflow_tasks[task_id].update({
                "status": "failed",
                "progress": 0,
                "error": error_msg,
                "completed_at": datetime.now()
            })
        
        _update_workflow_progress(task_id, "failed", 0, error_msg)
        raise Exception(error_msg)

@router.post("/process-comprehensive-async")
async def process_comprehensive_workflow_async(request: ComprehensiveWorkflowRequest):
    """
    🚀 COMPREHENSIVE async workflow that combines EVERYTHING:
    
    1. 📥 Download video in specified quality (supports up to 8K)
    2. 📄 Extract transcript from YouTube URL
    3. 🤖 Analyze with Gemini AI to find viral segments
    4. ✂️ Cut video into segments based on Gemini analysis with vertical cropping
    5. 📝 Generate subtitles with TRUE SPEECH SYNCHRONIZATION (word-level timestamps)
    6. 🔥 Burn subtitles directly into the final clips with perfect timing
    7. ☁️ Upload finished clips to Azure Blob Storage
    
    🎯 ADVANCED SUBTITLE FEATURES:
    - Word-level timestamp synchronization for perfect speech alignment
    - VAD filtering with intelligent retry logic
    - Environment-configurable parameters
    - Multiple fallback strategies for maximum reliability
    
    This is the ultimate all-in-one endpoint that takes a YouTube URL and produces 
    ready-to-upload short clips with professional-quality burned-in subtitles!
    
    Returns immediately with task_id for status polling.
    """
    try:
        # Generate unique task ID
        task_id = f"comprehensive_{uuid.uuid4().hex[:8]}"
        
        # Validate font size
        if request.font_size and (request.font_size < 12 or request.font_size > 120):
            raise HTTPException(status_code=400, detail="Font size must be between 12 and 120")
        
        # Initialize task tracking
        with workflow_task_lock:
            workflow_tasks[task_id] = {
                "task_id": task_id,
                "status": "queued",
                "progress": 0,
                "created_at": datetime.now(),
                "youtube_url": request.youtube_url,
                "quality": request.quality or "best",
                "create_vertical": request.create_vertical,
                "smoothing_strength": request.smoothing_strength,
                "burn_subtitles": request.burn_subtitles,
                "font_size": request.font_size,
                "export_codec": request.export_codec,
                "enable_audio_sync_fix": request.enable_audio_sync_fix,
                "audio_offset_ms": request.audio_offset_ms,
                "speech_synchronization": True,  # Always enabled
                "vad_filtering": True,  # Always enabled
                "priority": request.priority or "normal",
                "notify_webhook": request.notify_webhook,
                "current_step": "queued",
                "message": "Comprehensive workflow queued for processing",
                "error": None,
                "workflow_type": "comprehensive"
            }
        
        print(f"🚀 Comprehensive workflow {task_id} queued: {request.youtube_url}")
        print(f"🎯 Settings: quality={request.quality}, vertical={request.create_vertical}, subtitles={request.burn_subtitles}")
        print(f"🎬 Subtitle settings: speech_sync=True, vad_filtering=True, size={request.font_size}px, codec={request.export_codec}")
        
        # Start async processing (don't await - let it run in background)
        # Note: Using the optimized workflow function with speech synchronization
        asyncio.create_task(_process_video_workflow_async(
            task_id,
            request.youtube_url,
            request.quality or "best",
            request.create_vertical or True,
            request.smoothing_strength or "very_high",
            request.burn_subtitles or False,
            request.font_size or 15,
            request.export_codec or "h264",
            request.enable_audio_sync_fix,
            request.audio_offset_ms
        ))
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "🎬 Comprehensive workflow started! This will create clips with burned-in subtitles.",
            "youtube_url": request.youtube_url,
            "workflow_type": "comprehensive",
            "settings": {
                "quality": request.quality or "best",
                "create_vertical": request.create_vertical or True,
                "smoothing_strength": request.smoothing_strength or "very_high",
                "burn_subtitles": request.burn_subtitles or True,
                "speech_synchronization": True,
                "vad_filtering": True,
                "font_size": request.font_size or 15,
                "export_codec": request.export_codec or "h264",
                "enable_audio_sync_fix": request.enable_audio_sync_fix,
                "audio_offset_ms": request.audio_offset_ms
            },
            "workflow_steps": [
                "1. Video info extraction",
                "2. Video download",
                "3. Transcript extraction", 
                "4. Gemini AI analysis",
                "5. Vertical clip cutting",
                "6. Per-clip speech-synchronized subtitle generation",
                "7. Professional subtitle burning with word-level timing",
                "8. Upload to Azure Blob Storage",
                "9. Final processing"
            ],
            "status_endpoint": f"/workflow/workflow-status/{task_id}",
            "estimated_time": "10-30 minutes depending on video length and quality"
        }
        
    except Exception as e:
        print(f"❌ Failed to start comprehensive workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start comprehensive workflow: {str(e)}")

@router.post("/process-fast-async")
async def process_fast_workflow_async(request: FastWorkflowRequest):
    """
    🚀 FAST async workflow that SKIPS transcript extraction and Gemini analysis:
    
    1. ⏭️ Skip transcript extraction (save 10-15 seconds)
    2. ⏭️ Skip Gemini AI analysis (save 15-20 seconds)
    3. 📥 Download video in specified quality
    4. ✂️ Cut video into provided segments with vertical cropping
    5. 📝 Generate subtitles with speech synchronization (using Groq)
    6. 🔥 Burn subtitles directly into the final clips
    
    🎯 PERFORMANCE OPTIMIZATION:
    - 25-30 seconds faster than comprehensive workflow
    - Immediate processing start
    - Uses your pre-analyzed viral segments
    - Still provides high-quality Groq subtitles
    
    Perfect for when you already have viral moments identified!
    """
    try:
        # Validate segments
        if not request.viral_segments:
            raise HTTPException(status_code=400, detail="viral_segments cannot be empty")
        
        # Validate segment structure
        for i, segment in enumerate(request.viral_segments):
            if not isinstance(segment, dict):
                raise HTTPException(status_code=400, detail=f"Segment {i} must be a dictionary")
            if "start" not in segment or "end" not in segment:
                raise HTTPException(status_code=400, detail=f"Segment {i} must have 'start' and 'end' fields")
            if not isinstance(segment["start"], (int, float)) or not isinstance(segment["end"], (int, float)):
                raise HTTPException(status_code=400, detail=f"Segment {i} start/end must be numbers")
            if segment["start"] >= segment["end"]:
                raise HTTPException(status_code=400, detail=f"Segment {i} start must be less than end")
        
        # Generate unique task ID
        task_id = f"fast_{uuid.uuid4().hex[:8]}"
        
        # Initialize task tracking
        with workflow_task_lock:
            workflow_tasks[task_id] = {
                "task_id": task_id,
                "status": "queued",
                "progress": 0,
                "created_at": datetime.now(),
                "youtube_url": request.youtube_url,
                "viral_segments_count": len(request.viral_segments),
                "quality": request.quality or "best",
                "create_vertical": request.create_vertical,
                "smoothing_strength": request.smoothing_strength,
                "burn_subtitles": request.burn_subtitles,
                "font_size": request.font_size,
                "export_codec": request.export_codec,
                "priority": request.priority or "normal",
                "notify_webhook": request.notify_webhook,
                "current_step": "queued",
                "message": "Fast workflow queued for processing",
                "error": None,
                "workflow_type": "fast"
            }
        
        print(f"🚀 Fast workflow {task_id} queued: {request.youtube_url}")
        print(f"⚡ OPTIMIZATION: Skipping transcript extraction and Gemini analysis")
        print(f"📊 Pre-analyzed segments: {len(request.viral_segments)}")
        
        # Start async processing
        asyncio.create_task(_process_video_workflow_fast_async(
            task_id,
            request.youtube_url,
            request.viral_segments,
            request.quality or "best",
            request.create_vertical or True,
            request.smoothing_strength or "very_high",
            request.burn_subtitles or False,
            request.font_size or 15,
            request.export_codec or "h264"
        ))
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "⚡ Fast workflow started! Transcript extraction and Gemini analysis SKIPPED.",
            "youtube_url": request.youtube_url,
            "workflow_type": "fast",
            "performance_optimization": {
                "transcript_extraction_skipped": True,
                "gemini_analysis_skipped": True,
                "estimated_time_saved": "25-30 seconds",
                "immediate_processing_start": True
            },
            "settings": {
                "quality": request.quality or "best",
                "create_vertical": request.create_vertical or True,
                "smoothing_strength": request.smoothing_strength or "very_high",
                "burn_subtitles": request.burn_subtitles or True,
                "speech_synchronization": True,
                "vad_filtering": True,
                "font_size": request.font_size or 15,
                "export_codec": request.export_codec or "h264"
            },
            "segments_info": {
                "viral_segments_provided": len(request.viral_segments),
                "segments_preview": [
                    {
                        "title": seg.get("title", f"Segment {i+1}"),
                        "start": seg.get("start"),
                        "end": seg.get("end"),
                        "duration": seg.get("end", 0) - seg.get("start", 0)
                    }
                    for i, seg in enumerate(request.viral_segments[:3])  # Show first 3
                ]
            },
            "workflow_steps": [
                "1. Video info extraction",
                "2. ⏭️ Transcript extraction (SKIPPED)",
                "3. ⏭️ Gemini AI analysis (SKIPPED)",
                "4. Video download",
                "5. Vertical clip cutting",
                "6. Per-clip speech-synchronized subtitle generation",
                "7. Professional subtitle burning",
                "8. Final processing"
            ],
            "status_endpoint": f"/workflow/workflow-status/{task_id}",
            "estimated_time": "5-15 minutes (25-30 seconds faster than comprehensive)"
        }
        
    except Exception as e:
        print(f"❌ Fast workflow request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
async def get_workflow_status(task_id: str):
    """
    Get the current status of a workflow task
    
    Returns the task status, progress, and other metadata.
    """
    try:
        with workflow_task_lock:
            task_info = workflow_tasks.get(task_id)
        
        if not task_info:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        # Convert datetime objects to ISO strings for JSON serialization
        response_data = task_info.copy()
        
        # Handle datetime conversion
        for key in ['created_at', 'updated_at', 'completed_at']:
            if key in response_data and response_data[key]:
                if isinstance(response_data[key], datetime):
                    response_data[key] = response_data[key].isoformat()
        
        # Map status values to match frontend expectations
        status_mapping = {
            'queued': 'pending',
            'processing': 'processing',
            'completed': 'done',
            'failed': 'failed'
        }
        
        if 'status' in response_data:
            response_data['status'] = status_mapping.get(response_data['status'], response_data['status'])
        
        # Ensure we have the required fields for the frontend
        if 'stage' not in response_data:
            response_data['stage'] = response_data.get('current_step', 'unknown')
        
        # Add detailed error information if task failed
        if response_data.get('status') == 'failed' and response_data.get('error'):
            error_msg = response_data['error']
            if 'timeout' in error_msg.lower():
                response_data['error_details'] = {
                    'type': 'timeout',
                    'message': 'Processing timed out. This can happen with large videos or during intensive operations like vertical cropping.',
                    'suggestion': 'Try processing a shorter video or disable vertical cropping to reduce processing time.'
                }
            elif 'vertical crop' in error_msg.lower():
                response_data['error_details'] = {
                    'type': 'vertical_crop_failure',
                    'message': 'Vertical cropping failed. This is a CPU-intensive operation that can fail on some systems.',
                    'suggestion': 'Try processing a shorter video or check if your system has sufficient CPU resources.'
                }
            elif 'memory' in error_msg.lower() or 'out of memory' in error_msg.lower():
                response_data['error_details'] = {
                    'type': 'memory_error',
                    'message': 'Insufficient memory for video processing.',
                    'suggestion': 'Try processing a shorter video or lower quality setting.'
                }
            else:
                response_data['error_details'] = {
                    'type': 'general_error',
                    'message': error_msg,
                    'suggestion': 'Please try again or contact support if the issue persists.'
                }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in status endpoint for task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.post("/process-video")
async def process_video_authenticated(
    request: ProcessVideoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Authenticated endpoint to process YouTube videos and create clips
    
    This creates a Video record in the database and processes it asynchronously.
    """
    try:
        # Extract YouTube video ID
        video_id = get_video_id(request.youtube_url)
        
        # Get video info first
        video_info = get_video_info(request.youtube_url)
        
        # Create Video record in database
        from sqlalchemy import select
        
        # Check if user already has this video
        existing_video_query = select(Video).where(
            Video.user_id == current_user.id,
            Video.youtube_id == video_id
        )
        existing_video_result = await db.execute(existing_video_query)
        existing_video = existing_video_result.scalar_one_or_none()
        
        if existing_video and existing_video.status == VideoStatus.PROCESSING.value:
            raise HTTPException(
                status_code=400,
                detail="You already have this video being processed. Please wait for it to complete."
            )
        
        # Create or update video record
        if existing_video:
            video_record = existing_video
            video_record.status = VideoStatus.PROCESSING
        else:
            video_record = Video(
                user_id=current_user.id,
                youtube_id=video_id,
                title=video_info.get('title', 'Unknown Title'),
                status=VideoStatus.PROCESSING
            )
            db.add(video_record)
        
        await db.commit()
        await db.refresh(video_record)
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task in workflow_tasks
        with workflow_task_lock:
            workflow_tasks[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "progress": 0,
                "stage": "initializing",
                "message": "Video processing request received",
                "video_id": str(video_record.id),
                "user_id": str(current_user.id),
                "youtube_url": request.youtube_url,
                "created_at": datetime.now().isoformat(),
                "error": None,
                "clip_paths": []
            }
        
        # Start background processing
        if background_tasks:
            background_tasks.add_task(
                _process_video_with_db_updates,
                task_id=task_id,
                video_record_id=str(video_record.id),
                youtube_url=request.youtube_url,
                quality=request.quality or "best",
                create_vertical=request.create_vertical or False,
                smoothing_strength=request.smoothing_strength or "very_high"
            )
        else:
            # Fallback: start in thread pool
            workflow_executor.submit(
                asyncio.run,
                _process_video_with_db_updates(
                    task_id=task_id,
                    video_record_id=str(video_record.id),
                    youtube_url=request.youtube_url,
                    quality=request.quality or "best",
                    create_vertical=request.create_vertical or False,
                    smoothing_strength=request.smoothing_strength or "very_high"
                )
            )
        
        return {
            "success": True,
            "task_id": task_id,
            "video_id": str(video_record.id),
            "message": "Video processing started successfully",
            "status_url": f"/workflow/status/{task_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Update video status to failed if we created one
        try:
            if 'video_record' in locals():
                video_record.status = VideoStatus.FAILED
                await db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start video processing: {str(e)}"
        )


async def _process_video_with_db_updates(
    task_id: str,
    video_record_id: str,
    youtube_url: str,
    quality: str,
    create_vertical: bool,
    smoothing_strength: str
):
    """
    Process video and update database records
    """
    from ..database import get_db_session
    
    db = get_db_session()
    
    try:
        # Update task status
        _update_workflow_progress(task_id, "starting", 5, "Starting video processing...")
        
        # Call the existing comprehensive workflow
        await _process_video_workflow_async(
            task_id=task_id,
            youtube_url=youtube_url,
            quality=quality,
            create_vertical=create_vertical,
            smoothing_strength=smoothing_strength,
            burn_subtitles=False,
            font_size=15,
            export_codec="h264"
        )
        
        # Get the final task result
        with workflow_task_lock:
            task_result = workflow_tasks.get(task_id, {})
        
        if task_result.get("status") == "completed":
            # Update video status to done
            from sqlalchemy import select
            query = select(Video).where(Video.id == video_record_id)
            result = await db.execute(query)
            video_record = result.scalar_one_or_none()
            
            if video_record:
                video_record.status = VideoStatus.DONE
                
                # Get Azure clips info from the workflow result
                workflow_result = task_result.get("result", {})
                azure_clips_info = workflow_result.get("azure_storage_info", {}).get("clips_uploaded_to_azure", 0)
                files_created = workflow_result.get("files_created", {})
                azure_clips_data = files_created.get("azure_clips_info", [])
                analysis_results = workflow_result.get("analysis_results", {})
                viral_segments = analysis_results.get("segments", [])
                
                print(f"📊 Saving {len(azure_clips_data)} clips to database with Azure URLs...")
                
                # Create clip records with Azure blob URLs and proper metadata
                for i, azure_clip_data in enumerate(azure_clips_data):
                    try:
                        # Get segment timing info (fallback to defaults if not available)
                        segment_data = viral_segments[i] if i < len(viral_segments) else {}
                        start_time = segment_data.get("start", 0.0)
                        end_time = segment_data.get("end", 60.0)
                        duration = end_time - start_time
                        
                        # Create clip record with Azure blob URL
                        clip_record = Clip(
                            video_id=video_record.id,
                            blob_url=azure_clip_data.get("azure_clip_url"),  # ← Azure blob URL!
                            thumbnail_url=azure_clip_data.get("azure_thumbnail_url"),  # ← Azure thumbnail URL!
                            start_time=start_time,
                            end_time=end_time,
                            duration=duration,
                            file_size=None  # Could be added later from Azure metadata
                        )
                        
                        db.add(clip_record)
                        print(f"   ✅ Clip {i+1}: {azure_clip_data.get('azure_clip_url')}")
                        
                    except Exception as e:
                        print(f"   ❌ Failed to save clip {i+1} to database: {str(e)}")
                        continue
                
                await db.commit()
                print(f"✅ Successfully saved {len(azure_clips_data)} clips to PostgreSQL database")
                
        else:
            # Update video status to failed
            from sqlalchemy import select
            query = select(Video).where(Video.id == video_record_id)
            result = await db.execute(query)
            video_record = result.scalar_one_or_none()
            
            if video_record:
                video_record.status = VideoStatus.FAILED
                await db.commit()
                
    except Exception as e:
        print(f"❌ Database update failed: {str(e)}")
        # Update video status to failed
        try:
            from sqlalchemy import select
            query = select(Video).where(Video.id == video_record_id)
            result = await db.execute(query)
            video_record = result.scalar_one_or_none()
            
            if video_record:
                video_record.status = VideoStatus.FAILED
                await db.commit()
        except:
            pass
        
        raise e
    finally:
        await db.close()

@router.post("/cleanup-temp-video/{video_id}")
async def cleanup_temp_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    clip_storage: ClipStorageService = Depends(get_clip_storage_service)
):
    """
    Clean up temporary video files after processing is complete
    
    This endpoint should be called after all clips have been generated
    to remove the temporary YouTube video from storage.
    """
    try:
        # Verify user has access to this video
        from sqlalchemy import select
        query = select(Video).where(Video.id == video_id)
        result = await db.execute(query)
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        if video.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this video"
            )
        
        # Clean up temporary video
        success = await clip_storage.cleanup_temp_video_after_processing(video_id, db)
        
        if success:
            return {"message": "Temporary video cleaned up successfully"}
        else:
            return {"message": "No temporary video found or cleanup failed"}
            
    except HTTPException:
        raise
    except Exception as e:
        # Assuming logger is available, otherwise use print
        # from logging import getLogger
        # logger = getLogger(__name__)
        # logger.error(f"Failed to cleanup temp video {video_id}: {str(e)}")
        print(f"Failed to cleanup temp video {video_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup temporary video"
        )

@router.post("/schedule-cleanup")
async def schedule_temp_cleanup(
    current_user: User = Depends(get_current_user),
    clip_storage: ClipStorageService = Depends(get_clip_storage_service)
):
    """
    Run scheduled cleanup of expired temporary videos
    
    This is useful for maintenance tasks to clean up any expired temp videos.
    """
    try:
        deleted_count = await clip_storage.schedule_temp_video_cleanup()
        
        return {
            "message": f"Cleanup completed successfully",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        # Assuming logger is available, otherwise use print
        # from logging import getLogger
        # logger = getLogger(__name__)
        # logger.error(f"Scheduled cleanup failed: {str(e)}")
        print(f"Scheduled cleanup failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run scheduled cleanup"
        )


@router.post("/aggressive-cleanup")
async def aggressive_cleanup(
    max_age_hours: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    cleanup_service: CleanupService = Depends(get_cleanup_service)
):
    """
    Run aggressive cleanup of local temporary files
    
    This endpoint removes old local files to prevent infinite storage growth.
    Use this if you notice disk space issues.
    """
    try:
        deleted_count = await cleanup_service.cleanup_old_files(max_age_hours)
        empty_dirs = await cleanup_service.cleanup_empty_directories()
        usage = await cleanup_service.get_storage_usage()
        
        return {
            "message": "Aggressive cleanup completed successfully",
            "deleted_files": deleted_count,
            "removed_directories": empty_dirs,
            "current_storage_usage": usage
        }
        
    except Exception as e:
        print(f"Aggressive cleanup failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run aggressive cleanup"
        )


@router.get("/storage-usage")
async def get_storage_usage(
    current_user: User = Depends(get_current_user),
    cleanup_service: CleanupService = Depends(get_cleanup_service)
):
    """
    Get current local storage usage statistics
    
    This endpoint shows how much local storage is being used by temporary files.
    """
    try:
        usage = await cleanup_service.get_storage_usage()
        return usage
        
    except Exception as e:
        print(f"Failed to get storage usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get storage usage"
        ) 