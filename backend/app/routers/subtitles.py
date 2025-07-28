"""FastAPI router for subtitle processing endpoints."""

import os
import uuid
import logging
import time
import shutil
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pydub import AudioSegment

from app.services.groq_client import transcribe
from app.services.subs import convert_groq_to_subtitles
from app.services.burn_in import burn_subtitles_to_video
from app.exceptions import SubtitleError, TranscriptionError, SubtitleFormatError, BurnInError


logger = logging.getLogger(__name__)

router = APIRouter()


class SubtitleResponse(BaseModel):
    """Response model for subtitle processing."""
    task_id: str = Field(..., description="Unique task identifier")
    srt_path: str = Field(..., description="Path to the generated SRT file")
    vtt_path: str = Field(..., description="Path to the generated VTT file")
    burned_video_path: Optional[str] = Field(None, description="Path to video with burned-in subtitles")
    language: str = Field(..., description="Detected language code")
    cost_usd: float = Field(..., description="Estimated transcription cost in USD")
    latency_ms: int = Field(..., description="Total processing latency in milliseconds")
    original_filename: str = Field(..., description="Original uploaded filename")
    file_size_mb: float = Field(..., description="Uploaded file size in MB")


def _log_stage(task_id: str, stage: str, elapsed_ms: int) -> None:
    """Log structured stage information."""
    logger.info(f"task_id={task_id} stage={stage} elapsed_ms={elapsed_ms}")


def _cleanup_files(*file_paths: str) -> None:
    """Clean up temporary files."""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")


async def extract_audio_for_transcription(video_path: str, task_id: str) -> str:
    """Extract audio from video file for Groq transcription.
    
    Args:
        video_path: Path to the input video file
        task_id: Task ID for logging
        
    Returns:
        Path to the extracted audio file (WAV format)
        
    Raises:
        Exception: If audio extraction fails
    """
    try:
        # Create temporary audio file path
        temp_audio_path = f"{video_path}_audio_{task_id[:8]}.wav"
        
        logger.info(f"🎵 Extracting audio from {video_path} for transcription...")
        
        # Load video and extract audio
        audio = AudioSegment.from_file(video_path)
        
        # Convert to standard format for Groq (16kHz, mono, WAV)
        # Groq works best with these settings for transcription
        audio = audio.set_frame_rate(16000).set_channels(1)
        
        # Export as WAV
        audio.export(temp_audio_path, format="wav")
        
        # Verify file was created
        if not os.path.exists(temp_audio_path) or os.path.getsize(temp_audio_path) == 0:
            raise Exception("Audio extraction produced empty file")
        
        # Get audio duration for logging
        duration_s = len(audio) / 1000.0
        file_size_mb = os.path.getsize(temp_audio_path) / (1024 * 1024)
        
        logger.info(f"✅ Audio extracted successfully: {duration_s:.1f}s, {file_size_mb:.1f}MB")
        logger.debug(f"🎵 Audio file: {temp_audio_path}")
        
        return temp_audio_path
        
    except Exception as e:
        logger.error(f"❌ Audio extraction failed for task {task_id}: {str(e)}")
        
        # Clean up any partial file
        if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except:
                pass
        
        raise Exception(f"Audio extraction failed: {str(e)}")


@router.post("/subtitles", response_model=SubtitleResponse)
async def create_subtitles(
    video_file: UploadFile = File(..., description="Video file to process"),
    burn_in: bool = Form(True, description="Whether to burn subtitles into video"),
    font_size: int = Form(14, ge=12, le=120, description="Font size in pixels"),
    export_codec: str = Form("h264", description="Video codec for output (h264, h265, av1)"),
    disable_vad: bool = Form(True, description="Disable VAD filtering (enabled by default for better performance)"),
    speech_sync: bool = Form(False, description="Enable true speech synchronization using word-level timestamps"),
    background_tasks: BackgroundTasks = None
) -> SubtitleResponse:
    """Create subtitles for an uploaded video file.
    
    Upload a video file and get back:
    1. Transcription using Groq Whisper large-v3
    2. Generated SRT and VTT subtitle files
    3. Optionally, a video with burned-in subtitles
    
    Args:
        video_file: Uploaded video file (MP4, MOV, AVI, etc.)
        burn_in: Whether to burn subtitles into the video
        font_size: Font size in pixels
        export_codec: Video codec for output
        disable_vad: Disable VAD filtering (may help with continuous speech)
        background_tasks: FastAPI background tasks
        
    Returns:
        Subtitle processing response with file paths and metadata
        
    Raises:
        HTTPException: If processing fails
    """
    task_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Track files for cleanup
    temp_video_path = None
    srt_path = None
    vtt_path = None
    burned_video_path = None
    
    try:
        logger.info(f"🎬 Starting subtitle processing (task_id: {task_id})")
        logger.info(f"📁 Uploaded file: {video_file.filename} ({video_file.content_type})")
        logger.info(f"⚙️ Settings: VAD={'disabled' if disable_vad else 'enabled'}, burn_in={burn_in}")
        
        # Validate file type
        if not video_file.content_type or not video_file.content_type.startswith('video/'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {video_file.content_type}. Please upload a video file."
            )
        
        # Calculate file size
        file_size_mb = 0
        if hasattr(video_file, 'size') and video_file.size:
            file_size_mb = video_file.size / (1024 * 1024)
        
        # Create temporary directory for this task
        temp_dir = Path("temp_uploads") / task_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_extension = Path(video_file.filename).suffix or '.mp4'
        temp_video_path = str(temp_dir / f"input{file_extension}")
        
        _log_stage(task_id, "file_upload_start", 0)
        
        with open(temp_video_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        
        upload_elapsed = int((time.time() - start_time) * 1000)
        _log_stage(task_id, "file_upload_complete", upload_elapsed)
        
        # Verify file was saved correctly
        if not os.path.exists(temp_video_path) or os.path.getsize(temp_video_path) == 0:
            raise HTTPException(
                status_code=400,
                detail="Failed to save uploaded file or file is empty"
            )
        
        # If file size wasn't available from upload, calculate it now
        if file_size_mb == 0:
            file_size_mb = os.path.getsize(temp_video_path) / (1024 * 1024)
        
        logger.info(f"📊 File saved: {temp_video_path} ({file_size_mb:.2f} MB)")
        
        # Create output directory for subtitles
        output_dir = temp_dir / "output"
        output_dir.mkdir(exist_ok=True)
        
        filename_base = Path(video_file.filename).stem or f"video_{task_id[:8]}"
        
        # Stage 1: Audio Extraction + Transcription
        stage_start = time.time()
        _log_stage(task_id, "transcription_start", upload_elapsed)
        
        # Extract audio from video file for Groq transcription
        logger.info(f"🎵 Extracting audio from video for transcription...")
        audio_file_path = await extract_audio_for_transcription(temp_video_path, task_id)
        
        if not audio_file_path or not Path(audio_file_path).exists():
            raise Exception("Failed to extract audio from video file")
        
        logger.info(f"🎤 Starting transcription with Groq Whisper large-v3...")
        transcription_result = transcribe(
            file_path=audio_file_path,  # Use extracted audio file
            apply_vad=not disable_vad,  # Invert the disable flag
            task_id=task_id
        )
        
        # If we got no segments and VAD was enabled, try again without VAD
        if len(transcription_result["segments"]) == 0 and not disable_vad:
            logger.info(f"🔄 No segments found with VAD, retrying without VAD filtering...")
            transcription_result = transcribe(
                file_path=audio_file_path,  # Use extracted audio file
                apply_vad=False,
                task_id=f"{task_id}_retry"
            )
        # If we got very few segments and VAD was enabled, also retry without VAD
        elif len(transcription_result["segments"]) < 3 and not disable_vad:
            logger.info(f"🔄 Very few segments found with VAD ({len(transcription_result['segments'])}), retrying without VAD filtering...")
            retry_result = transcribe(
                file_path=audio_file_path,  # Use extracted audio file
                apply_vad=False,
                task_id=f"{task_id}_retry_few"
            )
            # Use the result with more segments
            if len(retry_result["segments"]) > len(transcription_result["segments"]):
                logger.info(f"✅ Better result without VAD: {len(retry_result['segments'])} vs {len(transcription_result['segments'])} segments")
                transcription_result = retry_result
        
        # Clean up extracted audio file
        try:
            if audio_file_path and Path(audio_file_path).exists():
                os.remove(audio_file_path)
                logger.debug(f"🧹 Cleaned up temporary audio file: {audio_file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up audio file {audio_file_path}: {e}")
        
        stage_elapsed = int((time.time() - stage_start) * 1000)
        _log_stage(task_id, "transcription_complete", stage_elapsed)
        
        logger.info(f"✅ Transcription complete: {len(transcription_result['segments'])} segments, language: {transcription_result['language']}")
        
        # Stage 2: Subtitle generation
        stage_start = time.time()
        _log_stage(task_id, "subtitle_generation_start", stage_elapsed)
        
        logger.info(f"📝 Generating SRT and VTT subtitle files...")
        
        # Configure subtitle processing parameters
        max_chars_per_line = int(os.getenv("SUBTITLE_MAX_CHARS_PER_LINE", 50))
        max_lines = int(os.getenv("SUBTITLE_MAX_LINES", 2))
        merge_gap_threshold = int(os.getenv("SUBTITLE_MERGE_GAP_MS", 200))
        
        # CapCut-style parameters
        capcut_mode = os.getenv("SUBTITLE_CAPCUT_MODE", "true").lower() == "true"
        min_word_duration = int(os.getenv("CAPCUT_MIN_WORD_DURATION_MS", 800))  # Increased for readability
        max_word_duration = int(os.getenv("CAPCUT_MAX_WORD_DURATION_MS", 1500))  # Increased for better flow
        word_overlap = int(os.getenv("CAPCUT_WORD_OVERLAP_MS", 150))  # Reduced overlap for clarity
        
        # Determine subtitle mode
        if speech_sync:
            mode_name = "Speech-synchronized"
            # Speech sync takes priority - disable capcut mode to avoid conflicts
            actual_capcut_mode = False
        elif capcut_mode:
            mode_name = "CapCut adaptive-word"
            actual_capcut_mode = True
        else:
            mode_name = "Traditional"
            actual_capcut_mode = False
        
        logger.info(f"🎬 Subtitle mode: {mode_name} style")
        
        # Get word timestamps for speech sync
        word_timestamps = transcription_result.get("word_timestamps", []) if speech_sync else None
        if speech_sync and word_timestamps:
            logger.info(f"🎯 Using {len(word_timestamps)} word timestamps for speech sync")
        elif speech_sync:
            logger.warning("⚠️ Speech sync requested but no word timestamps available, falling back to CapCut mode")
            actual_capcut_mode = True
        
        srt_path, vtt_path = convert_groq_to_subtitles(
            groq_segments=transcription_result["segments"],
            output_dir=str(output_dir),
            filename_base=filename_base,
            max_chars_per_line=max_chars_per_line,
            max_lines=max_lines,
            merge_gap_threshold_ms=merge_gap_threshold,
            capcut_mode=actual_capcut_mode,
            speech_sync_mode=speech_sync,
            word_timestamps=word_timestamps,
            min_word_duration_ms=min_word_duration,
            max_word_duration_ms=max_word_duration,
            word_overlap_ms=word_overlap
        )
        
        stage_elapsed = int((time.time() - stage_start) * 1000)
        _log_stage(task_id, "subtitle_generation_complete", stage_elapsed)
        
        logger.info(f"✅ Subtitle files created: {Path(srt_path).name}, {Path(vtt_path).name}")
        
        # Stage 3: Burn-in (if requested)
        if burn_in:
            stage_start = time.time()
            _log_stage(task_id, "burn_in_start", stage_elapsed)
            
            burned_video_path = str(output_dir / f"{filename_base}_subtitled.mp4")
            
            logger.info(f"🔥 Burning subtitles into video...")
            burned_video_path = burn_subtitles_to_video(
                video_path=temp_video_path,
                srt_path=srt_path,
                output_path=burned_video_path,
                font_size=font_size,
                export_codec=export_codec,
                task_id=task_id
            )
            
            stage_elapsed = int((time.time() - stage_start) * 1000)
            _log_stage(task_id, "burn_in_complete", stage_elapsed)
            
            logger.info(f"✅ Burned-in video created: {Path(burned_video_path).name}")
        else:
            logger.info("⏭️ Skipping subtitle burn-in (burn_in=false)")
        
        # Calculate total latency
        total_latency_ms = int((time.time() - start_time) * 1000)
        
        # Schedule cleanup of temporary input video (keep outputs for download)
        if background_tasks:
            background_tasks.add_task(_cleanup_files, temp_video_path)
        
        response = SubtitleResponse(
            task_id=task_id,
            srt_path=srt_path,
            vtt_path=vtt_path,
            burned_video_path=burned_video_path,
            language=transcription_result["language"],
            cost_usd=transcription_result["cost_usd"],
            latency_ms=total_latency_ms,
            original_filename=video_file.filename,
            file_size_mb=round(file_size_mb, 2)
        )
        
        logger.info(f"🎉 Subtitle processing completed (task_id: {task_id}) - {total_latency_ms}ms")
        logger.info(f"📊 Final stats: {len(transcription_result['segments'])} segments, "
                   f"${transcription_result['cost_usd']:.4f} cost, {response.file_size_mb}MB processed")
        
        return response
        
    except TranscriptionError as e:
        logger.error(f"Transcription error (task_id: {task_id}): {e.message}")
        _cleanup_files(temp_video_path, srt_path, vtt_path, burned_video_path)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e.message}")
    
    except SubtitleFormatError as e:
        logger.error(f"Subtitle format error (task_id: {task_id}): {e.message}")
        _cleanup_files(temp_video_path, srt_path, vtt_path, burned_video_path)
        raise HTTPException(status_code=500, detail=f"Subtitle generation failed: {e.message}")
    
    except BurnInError as e:
        logger.error(f"Burn-in error (task_id: {task_id}): {e.message}")
        _cleanup_files(temp_video_path, srt_path, vtt_path, burned_video_path)
        raise HTTPException(status_code=500, detail=f"Subtitle burn-in failed: {e.message}")
    
    except SubtitleError as e:
        logger.error(f"Subtitle error (task_id: {task_id}): {e.message}")
        _cleanup_files(temp_video_path, srt_path, vtt_path, burned_video_path)
        raise HTTPException(status_code=500, detail=f"Subtitle processing failed: {e.message}")
    
    except Exception as e:
        logger.error(f"Unexpected error (task_id: {task_id}): {str(e)}")
        _cleanup_files(temp_video_path, srt_path, vtt_path, burned_video_path)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/subtitles/download/{file_type}/{task_id}/{filename}")
async def download_subtitle_file(
    file_type: str,
    task_id: str, 
    filename: str
):
    """Download generated subtitle or video files.
    
    Args:
        file_type: Type of file (srt, vtt, video)
        task_id: Task ID from subtitle processing
        filename: Name of the file to download
        
    Returns:
        File download response
    """
    try:
        # Construct file path
        base_dir = Path("temp_uploads") / task_id / "output"
        file_path = base_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type
        media_type_map = {
            'srt': 'text/plain',
            'vtt': 'text/vtt',
            'video': 'video/mp4'
        }
        
        media_type = media_type_map.get(file_type, 'application/octet-stream')
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail="Download failed")


@router.get("/subtitles/health")
async def health_check():
    """Health check endpoint for subtitle service."""
    try:
        # Basic import test
        from app.services.groq_client import GroqClient
        from app.services.burn_in import BurnInRenderer
        
        # Test Groq API key
        groq_key = os.getenv("GROQ_API_KEY")
        groq_available = bool(groq_key)
        
        # Test FFmpeg availability
        try:
            renderer = BurnInRenderer()
            ffmpeg_available = True
        except Exception:
            ffmpeg_available = False
        
        # Check temp directory
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        temp_writable = os.access(temp_dir, os.W_OK)
        
        return {
            "status": "healthy",
            "service": "subtitle_processor",
            "groq_api_available": groq_available,
            "ffmpeg_available": ffmpeg_available,
            "temp_directory_writable": temp_writable,
            "temp_directory": str(temp_dir.absolute())
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        ) 