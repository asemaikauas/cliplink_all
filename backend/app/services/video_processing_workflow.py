"""
Enhanced Video Processing Workflow with Audio Sync Management

This module provides an enhanced video processing workflow that maintains
audio/video synchronization throughout the entire processing pipeline.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .youtube import youtube_service, get_video_id
from .transcript import fetch_youtube_transcript_with_word_timestamps
from .gemini import analyze_transcript_for_viral_segments
from .vertical_crop_async import get_async_vertical_crop_service
from .burn_in import BurnInRenderer
from .audio_sync_manager import get_audio_sync_manager
from .subs import convert_groq_to_subtitles

logger = logging.getLogger(__name__)

class EnhancedVideoProcessingWorkflow:
    """Enhanced video processing workflow with audio sync management"""
    
    def __init__(self):
        self.burn_in_renderer = BurnInRenderer()
    
    async def process_video_with_sync_preservation(
        self,
        youtube_url: str,
        quality: str = "best",
        create_vertical: bool = True,
        smoothing_strength: str = "very_high",
        burn_subtitles: bool = True,
        font_size: int = 15,
        export_codec: str = "h264",
        enable_audio_sync_fix: bool = True,
        audio_offset_ms: float = 0.0,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process video with comprehensive audio sync management
        
        Args:
            youtube_url: YouTube video URL
            quality: Video quality (best, 8k, 4k, etc.)
            create_vertical: Whether to create vertical crops
            smoothing_strength: Smoothing level for cropping
            burn_subtitles: Whether to burn subtitles
            font_size: Subtitle font size
            export_codec: Video codec
            enable_audio_sync_fix: Whether to apply audio sync corrections
            audio_offset_ms: Manual audio offset correction in milliseconds
            task_id: Task ID for tracking
            
        Returns:
            Processing results with sync status
        """
        try:
            logger.info(f"🚀 Starting enhanced video processing with sync preservation (task_id: {task_id})")
            
            # Initialize services
            sync_manager = await get_audio_sync_manager()
            crop_service = await get_async_vertical_crop_service()
            
            # Step 1: Download video
            logger.info("📥 Downloading video...")
            video_id = get_video_id(youtube_url)
            download_result = await youtube_service.download_video_async(youtube_url, quality)
            
            if not download_result["success"]:
                raise Exception(f"Video download failed: {download_result.get('error', 'Unknown error')}")
            
            source_video_path = Path(download_result["video_path"])
            
            # Step 2: Audio sync analysis (if enabled)
            if enable_audio_sync_fix:
                logger.info("🔊 Analyzing audio/video synchronization...")
                detected_offset = await sync_manager.detect_av_sync_offset(source_video_path)
                total_offset = detected_offset * 1000 + audio_offset_ms  # Convert to ms and add manual offset
                
                if abs(total_offset) > 10:  # Only apply if significant
                    logger.info(f"🔧 Applying audio sync correction: {total_offset:.1f}ms")
                    
                    # Create sync-corrected source video
                    corrected_video_path = source_video_path.with_name(f"{source_video_path.stem}_sync_corrected.mp4")
                    
                    success = await sync_manager.create_sync_corrected_video(
                        source_video_path, corrected_video_path, total_offset
                    )
                    
                    if success:
                        source_video_path = corrected_video_path
                        logger.info("✅ Audio sync correction applied to source video")
                    else:
                        logger.warning("⚠️ Audio sync correction failed, using original video")
            
            # Step 3: Get transcript with word timestamps
            logger.info("📝 Extracting transcript with word timing...")
            transcript_result = await fetch_youtube_transcript_with_word_timestamps(youtube_url)
            
            if not transcript_result["success"]:
                raise Exception(f"Transcript extraction failed: {transcript_result.get('error')}")
            
            # Step 4: Analyze for viral segments
            logger.info("🤖 Analyzing transcript for viral segments...")
            analysis_result = await analyze_transcript_for_viral_segments(
                transcript_result["transcript"], transcript_result["word_timestamps"]
            )
            
            if not analysis_result["success"]:
                raise Exception(f"Transcript analysis failed: {analysis_result.get('error')}")
            
            viral_segments = analysis_result["segments"]
            logger.info(f"🎯 Found {len(viral_segments)} viral segments")
            
            # Step 5: Process segments with enhanced sync
            processed_clips = []
            
            for i, segment in enumerate(viral_segments):
                logger.info(f"🎬 Processing segment {i+1}/{len(viral_segments)}: {segment['start']:.1f}s - {segment['end']:.1f}s")
                
                # Create segment clip
                segment_path = source_video_path.parent / f"segment_{i+1}_{video_id}.mp4"
                
                # Use FFmpeg with sync preservation for clipping
                await self._create_segment_with_sync(
                    source_video_path, segment_path, segment['start'], segment['end'], sync_manager
                )
                
                # Apply vertical cropping with sync preservation
                if create_vertical:
                    crop_output_path = segment_path.with_name(f"{segment_path.stem}_vertical.mp4")
                    
                    crop_result = await crop_service.create_vertical_crop_async(
                        segment_path, crop_output_path,
                        use_speaker_detection=True,
                        smoothing_strength=smoothing_strength,
                        task_id=f"{task_id}_seg_{i+1}" if task_id else None
                    )
                    
                    if crop_result.get("success"):
                        segment_path = crop_output_path
                        logger.info(f"✅ Vertical crop completed for segment {i+1}")
                    else:
                        logger.warning(f"⚠️ Vertical crop failed for segment {i+1}, using original")
                
                # Burn subtitles with sync preservation
                if burn_subtitles:
                    # Generate subtitles for this segment
                    segment_word_timestamps = [
                        word for word in transcript_result["word_timestamps"]
                        if segment['start'] <= word.get('start', 0) <= segment['end']
                    ]
                    
                    if segment_word_timestamps:
                        # Adjust timestamps for segment
                        adjusted_timestamps = []
                        for word in segment_word_timestamps:
                            adjusted_word = word.copy()
                            adjusted_word['start'] = max(0, word.get('start', 0) - segment['start'])
                            adjusted_word['end'] = max(0, word.get('end', 0) - segment['start'])
                            adjusted_timestamps.append(adjusted_word)
                        
                        # Generate SRT file
                        srt_path, _ = await convert_groq_to_subtitles(
                            [], segment_path.parent, f"segment_{i+1}_{video_id}",
                            word_timestamps=adjusted_timestamps
                        )
                        
                        if srt_path and Path(srt_path).exists():
                            # Burn subtitles with sync preservation
                            subtitled_path = segment_path.with_name(f"{segment_path.stem}_subtitled.mp4")
                            
                            try:
                                result_path = await self.burn_in_renderer.burn_subtitles_async(
                                    str(segment_path), str(srt_path), str(subtitled_path),
                                    font_size=font_size, export_codec=export_codec,
                                    task_id=f"{task_id}_sub_{i+1}" if task_id else None
                                )
                                
                                if result_path and Path(result_path).exists():
                                    segment_path = Path(result_path)
                                    logger.info(f"✅ Subtitles burned for segment {i+1}")
                                else:
                                    logger.warning(f"⚠️ Subtitle burning failed for segment {i+1}")
                                    
                            except Exception as e:
                                logger.warning(f"⚠️ Subtitle burning error for segment {i+1}: {e}")
                
                # Add to processed clips
                processed_clips.append({
                    "segment_index": i + 1,
                    "file_path": str(segment_path),
                    "start_time": segment['start'],
                    "end_time": segment['end'],
                    "duration": segment['end'] - segment['start'],
                    "title": segment.get('title', f'Segment {i+1}'),
                    "sync_preserved": enable_audio_sync_fix
                })
            
            logger.info(f"✅ Enhanced video processing completed: {len(processed_clips)} clips created")
            
            return {
                "success": True,
                "clips": processed_clips,
                "source_video": str(source_video_path),
                "transcript": transcript_result["transcript"],
                "viral_segments": viral_segments,
                "sync_correction_applied": enable_audio_sync_fix,
                "total_audio_offset_ms": total_offset if enable_audio_sync_fix else 0,
                "processing_summary": {
                    "total_segments": len(viral_segments),
                    "successful_clips": len(processed_clips),
                    "vertical_cropping": create_vertical,
                    "subtitle_burning": burn_subtitles,
                    "sync_preservation": enable_audio_sync_fix
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced video processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "clips": [],
                "sync_correction_applied": False
            }
    
    async def _create_segment_with_sync(
        self, 
        source_path: Path, 
        output_path: Path, 
        start: float, 
        end: float,
        sync_manager
    ) -> bool:
        """Create video segment with sync preservation"""
        try:
            # Use sync manager's enhanced clipping
            cmd = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-ss', str(start),
                '-i', str(source_path),
                '-t', str(end - start),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-crf', '18',
                '-preset', 'medium',
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                '-movflags', '+faststart',
                '-y', str(output_path)  # FIXED: -y flag before output path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Segment creation failed: {e}")
            return False

# Global instance
enhanced_workflow = EnhancedVideoProcessingWorkflow()

async def get_enhanced_video_workflow() -> EnhancedVideoProcessingWorkflow:
    """Get the enhanced video processing workflow instance"""
    return enhanced_workflow 