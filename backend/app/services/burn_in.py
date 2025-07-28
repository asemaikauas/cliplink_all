"""Subtitle burn-in renderer using FFmpeg."""

import os
import subprocess
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from app.exceptions import BurnInError


logger = logging.getLogger(__name__)


class BurnInRenderer:
    """FFmpeg-based subtitle burn-in renderer."""
    
    def __init__(self):
        """Initialize burn-in renderer."""
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self) -> None:
        """Verify FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise BurnInError("FFmpeg not found or not working properly")
            logger.info("FFmpeg verified successfully")
        except FileNotFoundError:
            raise BurnInError("FFmpeg not found. Please install FFmpeg.")
        except subprocess.TimeoutExpired:
            raise BurnInError("FFmpeg verification timed out")
        except Exception as e:
            raise BurnInError(f"FFmpeg verification failed: {str(e)}")
    
    def _build_force_style(
        self,
        font_size: int = 15,                   # Fixed font size in pixels (much more reliable)
        font_name: str = "Inter",            # Bold, thick font for maximum impact
        primary_colour: str = "&H00FFFFFF&",   # solid white text
        back_colour: str = "&HE6000000&",      # Very opaque black box
        border_style: int = 1,                 # 1 = outline + drop shadow style
        shadow: int = 1,                       # drop shadow for depth
        shadow_colour: str = "&HA6999999&",    # semi-transparent gray shadow
        outline: int = 1,                      # black outline for better contrast
        outline_colour: str = "&H00000000&",   # solid black outline 
        alignment: int = 2,                    # bottom-centre
        margin_v: int = 50,                    # bottom margin
        bold: int = 1,                         # force bold text (1 = enabled)

    ) -> str:
        """Build ASS subtitle force_style string with improved visibility.
        
        Args:
            font_size: Font size in pixels (15px clean and readable)
            font_name: Font family name (Inter for modern look)
            primary_colour: Primary text color in ASS format (white)
            back_colour: Background color in ASS format (very opaque black box)
            border_style: Border style (1 = outline + shadow)
            outline: Outline thickness in pixels
            outline_colour: Outline color (black for contrast)
            shadow: Shadow distance in pixels
            shadow_colour: Shadow color (semi-transparent gray)
            alignment: Text alignment (2 = bottom center)
            margin_v: Bottom margin in pixels
            bold: Bold text flag (1 = enabled)
            scale_y: Vertical scaling percentage (90 = 90% height for shorter letters)
            
        Returns:
            Force style string for FFmpeg with enhanced visibility
        """
        # Use fixed font size for reliable results
        force_style = (
            f"Fontname={font_name},"
            f"Fontsize={font_size},"
            f"PrimaryColour={primary_colour},"
            f"BackColour={back_colour},"
            f"BorderStyle={border_style},"
            f"Outline={outline},"
            f"OutlineColour={outline_colour},"
            f"Shadow={shadow},"
            f"ShadowColour={shadow_colour},"
            f"Bold={bold},"
            f"Alignment={alignment},"
            f"MarginV={margin_v}"
        )
        
        return force_style

    async def burn_subtitles_async(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        font_size: int = 14,
        export_codec: str = "h264",
        crf: int = 18,
        task_id: Optional[str] = None
    ) -> str:
        """Burn subtitles into video using enhanced sync preservation (async version).
        
        Args:
            video_path: Path to input video file
            srt_path: Path to SRT subtitle file
            output_path: Path for output video file
            font_size: Font size in pixels
            export_codec: Video codec (h264, h265, etc.)
            crf: Constant Rate Factor for video quality
            task_id: Task ID for logging
            
        Returns:
            Path to the output video file
            
        Raises:
            BurnInError: If burn-in process fails
        """
        try:
            from .audio_sync_manager import get_audio_sync_manager
            
            logger.info(f"🔊 Starting enhanced subtitle burn-in with sync preservation (task_id: {task_id})")
            
            # Use the enhanced audio sync manager
            sync_manager = await get_audio_sync_manager()
            
            success = await sync_manager.fix_subtitle_burn_sync(
                video_path, srt_path, output_path, font_size, export_codec, crf
            )
            
            if success:
                logger.info(f"✅ Enhanced subtitle burn-in completed: {output_path}")
                return output_path
            else:
                # Fallback to original method
                logger.warning("Enhanced subtitle burn failed, using fallback method...")
                return self.burn_subtitles(video_path, srt_path, output_path, font_size, export_codec, crf, task_id)
                
        except Exception as e:
            logger.error(f"Enhanced subtitle burn error: {e}")
            # Fallback to original method
            return self.burn_subtitles(video_path, srt_path, output_path, font_size, export_codec, crf, task_id)
    
    def burn_subtitles(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        font_size: int = 14,
        export_codec: str = "h264",
        crf: int = 18,
        task_id: Optional[str] = None
    ) -> str:
        """Burn subtitles into video using FFmpeg.
        
        Args:
            video_path: Path to input video file
            srt_path: Path to SRT subtitle file
            output_path: Path for output video file
            font_size: Font size in pixels (15px clean and readable)
            export_codec: Video codec (h264, h265, etc.)
            crf: Constant Rate Factor for video quality (lower = higher quality)
            task_id: Task ID for logging
            
        Returns:
            Path to the output video file
            
        Raises:
            BurnInError: If burn-in process fails
        """
        try:
            logger.info(f"Starting subtitle burn-in (task_id: {task_id})")
            logger.info(f"Input video: {video_path}")
            logger.info(f"SRT file: {srt_path}")
            logger.info(f"Output: {output_path}")
            
            # Verify input files exist
            if not os.path.exists(video_path):
                raise BurnInError(f"Input video not found: {video_path}")
            if not os.path.exists(srt_path):
                raise BurnInError(f"SRT file not found: {srt_path}")
            
            # Create output directory if needed
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Build force style for subtitles
            force_style = self._build_force_style(font_size=font_size)
            
            # Build FFmpeg command
            # Map export codecs to FFmpeg codec names
            codec_mapping = {
                "h264": "libx264",
                "h265": "libx265", 
                "av1": "libaom-av1"
            }
            video_codec = codec_mapping.get(export_codec, "libx264")
            
            # Escape the SRT path for FFmpeg (handle spaces and special characters)
            # Also ensure the path is clean ASCII
            import unicodedata
            import re
            
            # First normalize and clean the path
            try:
                # Normalize path and convert to ASCII
                clean_srt_path = unicodedata.normalize('NFKD', srt_path)
                clean_srt_path = clean_srt_path.encode('ascii', 'ignore').decode('ascii')
            except Exception:
                # Fallback: use original path
                clean_srt_path = srt_path
            
            # Escape for FFmpeg
            escaped_srt_path = clean_srt_path.replace("\\", "\\\\").replace(":", "\\:")
            
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"subtitles='{escaped_srt_path}':force_style='{force_style}'",
                "-c:v", video_codec,
                "-crf", str(crf),
                "-c:a", "copy",  # Copy audio without re-encoding
                "-y",  # Overwrite output file
                output_path
            ]
            
            logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            # Execute FFmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,  # Use binary mode to avoid encoding issues
                timeout=3600  # 1 hour timeout for long videos
            )
            
            if result.returncode != 0:
                error_msg = f"FFmpeg failed with return code {result.returncode}"
                if result.stderr:
                    # Safely decode stderr with error handling
                    try:
                        stderr_text = result.stderr.decode('utf-8', errors='replace')
                    except Exception:
                        stderr_text = str(result.stderr)
                    error_msg += f"\nSTDERR: {stderr_text}"
                raise BurnInError(error_msg)
            
            # Verify output file was created
            if not os.path.exists(output_path):
                raise BurnInError("Output file was not created")
            
            output_size = os.path.getsize(output_path)
            logger.info(
                f"Subtitle burn-in completed (task_id: {task_id}) - "
                f"output: {output_path} ({output_size / (1024*1024):.1f} MB)"
            )
            
            return output_path
            
        except subprocess.TimeoutExpired:
            raise BurnInError("FFmpeg process timed out (>1 hour)")
        except Exception as e:
            logger.error(f"Subtitle burn-in failed (task_id: {task_id}): {str(e)}")
            raise BurnInError(f"Subtitle burn-in failed: {str(e)}", task_id=task_id)
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get video information using FFprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video metadata
            
        Raises:
            BurnInError: If getting video info fails
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise BurnInError(f"FFprobe failed: {result.stderr}")
            
            import json
            return json.loads(result.stdout)
            
        except Exception as e:
            raise BurnInError(f"Failed to get video info: {str(e)}")


def burn_subtitles_to_video(
    video_path: str,
    srt_path: str,
    output_path: str,
    font_size: int = 14,
    export_codec: str = "h264",
    crf: int = 18,
    task_id: Optional[str] = None
) -> str:
    """Convenience function to burn subtitles into video.
    
    Args:
        video_path: Path to input video file
        srt_path: Path to SRT subtitle file
        output_path: Path for output video file
        font_size: Font size in pixels (14px clean and readable)
        export_codec: Video codec (h264, h265, etc.)
        crf: Constant Rate Factor for video quality
        task_id: Task ID for logging
        
    Returns:
        Path to the output video file
    """
    renderer = BurnInRenderer()
    return renderer.burn_subtitles(
        video_path, srt_path, output_path, font_size, export_codec, crf, task_id
    ) 