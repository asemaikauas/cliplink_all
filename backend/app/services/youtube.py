import logging
import os
import subprocess
import requests
import tempfile
import json
from pathlib import Path
from typing import List, Dict, Optional
from moviepy import VideoFileClip
import asyncio
from apify_client import ApifyClient
from dotenv import load_dotenv
import shutil

# Load environment variables
load_dotenv()

# Import vertical cropping service
try:
    from .vertical_crop import crop_video_to_vertical
    VERTICAL_CROP_AVAILABLE = True
    print("✅ Vertical cropping service loaded")
except ImportError as e:
    VERTICAL_CROP_AVAILABLE = False
    print(f"⚠️ Vertical cropping not available: {e}")

# Configure MoviePy to use the system ffmpeg if available
try:
    import imageio_ffmpeg
    # Try to set ffmpeg path explicitly
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    if ffmpeg_path:
        os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg_path
        print(f"🎬 Using ffmpeg: {ffmpeg_path}")
    else:
        print("⚠️ Could not find ffmpeg via imageio-ffmpeg, trying system PATH")
except Exception as e:
    print(f"⚠️ FFmpeg configuration warning: {e}")
    print("🔧 MoviePy will try to use system ffmpeg")

# Setup logging
logger = logging.getLogger(__name__)

def create_clip_with_direct_ffmpeg(video_path: Path, start: float, end: float, output_path: Path) -> bool:
    """
    Fallback function to create clips using direct ffmpeg calls with proper error handling.
    This addresses the 'NoneType' object has no attribute 'stdout' issue.
    """
    try:
        cmd = [
            'ffmpeg',
            '-hide_banner', '-loglevel', 'error',
            '-ss', str(start),
            '-i', str(video_path),
            '-t', str(end - start),
            '-c', 'copy',  # Copy streams without re-encoding for speed
            '-avoid_negative_ts', 'make_zero',
            str(output_path),
            '-y'  # Overwrite output file
        ]
        
        # Use subprocess.run with proper error handling (as suggested in the original query)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return True
        else:
            print(f"❌ FFmpeg stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ FFmpeg timeout after 300 seconds")
        return False
    except Exception as e:
        print(f"❌ FFmpeg exception: {str(e)}")
        return False

class DownloadError(Exception):
    """Custom exception for video download errors"""
    pass

class YouTubeService:
    """
    YouTube service using Apify YouTube Video Downloader API
    """
    def __init__(self, downloads_dir: str = "downloads"):
        self.downloads_dir = Path(downloads_dir)
        self.downloads_dir.mkdir(exist_ok=True)
        
        # Get Apify API token from environment
        self.apify_token = os.getenv("APIFY_TOKEN")
        if not self.apify_token:
            raise ValueError("APIFY_TOKEN environment variable not set. Please add your Apify API token to the .env file.")
        
        # Initialize Apify client
        self.client = ApifyClient(self.apify_token)
        
        # Quality mapping for Apify Actor
        self.quality_map = {
            "8k": "2160p",  # Apify supports up to 4320p but we'll use 2160p as fallback for 8k
            "4k": "2160p",
            "1440p": "1440p",
            "1080p": "1080p", 
            "720p": "720p",
            "best": "1080p"  # Default to 1080p for best
        }

    def get_video_info(self, url: str) -> Dict:
        """
        Extract basic video information from YouTube URL - just get video ID and title
        """
        try:
            print(f"📺 Getting basic video info for: {url}")
            
            # Just extract the video ID from URL for faster processing
            basic_info = self._extract_video_id_from_url(url)
            video_id = basic_info['id']
            
            print(f"✅ Video ID extracted: {video_id}")
            
            # Return minimal info needed for the application
            return {
                'id': video_id,
                'title': 'Unknown Title',  # Will be populated during download
                'duration': None,
                'view_count': None,
                'upload_date': None,
                'uploader': None,
                'description': None,
                'is_live': False,
                'availability': 'public'
            }
        except Exception as e:
            raise DownloadError(f"Failed to extract video info: {str(e)}")

    def get_available_formats(self, url: str) -> List[Dict]:
        """
        Get list of available video formats - simplified for Apify API
        """
        try:
            # Apify Actor supports these resolutions
            available_formats = [
                {
                    'format_id': '4320p',
                    'ext': 'mp4',
                    'resolution': '7680x4320',
                    'height': 4320,
                    'width': 7680,
                    'fps': 30,
                    'filesize': 0,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'format_note': '8K (4320p)'
                },
                {
                    'format_id': '2160p',
                    'ext': 'mp4',
                    'resolution': '3840x2160',
                    'height': 2160,
                    'width': 3840,
                    'fps': 30,
                    'filesize': 0,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'format_note': '4K (2160p)'
                },
                {
                    'format_id': '1440p',
                    'ext': 'mp4',
                    'resolution': '2560x1440',
                    'height': 1440,
                    'width': 2560,
                    'fps': 30,
                    'filesize': 0,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'format_note': '2K (1440p)'
                },
                {
                    'format_id': '1080p',
                    'ext': 'mp4',
                    'resolution': '1920x1080',
                    'height': 1080,
                    'width': 1920,
                    'fps': 30,
                    'filesize': 0,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'format_note': 'Full HD (1080p)'
                },
                {
                    'format_id': '720p',
                    'ext': 'mp4',
                    'resolution': '1280x720',
                    'height': 720,
                    'width': 1280,
                    'fps': 30,
                    'filesize': 0,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'format_note': 'HD (720p)'
                }
            ]
            
            return available_formats
                
        except Exception as e:
            raise DownloadError(f"Failed to get available formats: {str(e)}")

    async def download_video(self, url: str, quality: str = "best") -> Path:
        """
        Download YouTube video using Apify YouTube Video Downloader API
        """
        try:
            logger.info(f"🎬 Starting Apify download: {url} (quality: {quality})")
            
            video_id_info = self._extract_video_id_from_url(url)
            video_id = video_id_info["id"]
            
            # Check if already downloaded
            existing_file = self._find_downloaded_file(video_id, quality)
            if existing_file:
                logger.info(f"✅ Using existing download: {existing_file}")
                return existing_file
            
            # Map quality to Apify-supported resolution
            apify_quality = self.quality_map.get(quality, "1080p")
            logger.info(f"📊 Mapped quality '{quality}' to Apify resolution: {apify_quality}")
            
            # Call Apify YouTube Video Downloader Actor
            logger.info("🔄 Calling Apify YouTube Video Downloader...")
            run_input = {
                "urls": [url],
                "quality": apify_quality,
                "downloadMode": "video"
            }
            
            # Run the Apify Actor
            run = self.client.actor("xtech/youtube-video-downloader").call(run_input=run_input)
            
            # Get results from the Actor run
            results = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)
            
            if not results:
                raise DownloadError("No download results returned from Apify")
            
            result = results[0]
            
            # Check if download was successful
            if not result.get("downloadUrl"):
                error_msg = result.get("error", "Unknown error from Apify")
                raise DownloadError(f"Apify download failed: {error_msg}")
            
            download_url = result["downloadUrl"]
            title = result.get("title", "Unknown Title")
            resolution = result.get("resolution", apify_quality)
            
            logger.info(f"📥 Got download URL from Apify. Title: {title}")
            logger.info(f"📊 Resolution: {resolution}")
            
            # Download the video file from Apify's download URL
            downloaded_file = self._download_file_from_url(download_url, video_id, title, resolution)
            
            logger.info(f"📁 Downloaded: {downloaded_file}")
            
            # 🔧 PREPROCESSING: Check codec and convert AV1 to H.264 if needed
            processed_file = await self._preprocess_video_for_compatibility(downloaded_file)
            
            return processed_file
            
        except Exception as e:
            logger.error(f"Apify download failed: {str(e)}")
            if "Video unavailable" in str(e):
                raise DownloadError(f"Video is unavailable or private: {url}")
            elif "private" in str(e).lower():
                raise DownloadError(f"Video is private or restricted: {url}")
            else:
                raise DownloadError(f"Download failed: {str(e)}")

    async def _preprocess_video_for_compatibility(self, video_path: Path) -> Path:
        """
        Preprocess video during download: convert AV1 to H.264 for fast processing
        
        Returns:
            Path to processed video (original or converted H.264 version)
        """
        try:
            # Detect video codec
            codec_info = self._verify_video_codec(video_path)
            video_codec = codec_info.get("video_codec", "").lower()
            
            logger.info(f"🎬 Detected codec: {video_codec}")
            
            # If it's already H.264, no conversion needed
            if video_codec in ["h264", "avc1"]:
                logger.info(f"✅ Video is already H.264 - no conversion needed")
                return video_path
            
            # If it's AV1, convert to H.264 during download (user expects to wait)
            if video_codec == "av1":
                logger.info(f"🔄 AV1 detected - converting to H.264 for fast processing...")
                h264_path = await self._convert_av1_to_h264_async(video_path)
                
                if h264_path and h264_path.exists() and h264_path != video_path:
                    # Verify the conversion worked
                    h264_codec_info = self._verify_video_codec(h264_path)
                    if h264_codec_info.get("video_codec", "").lower() in ["h264", "avc1"]:
                        logger.info(f"✅ H.264 conversion successful: {h264_path}")
                        
                        # Keep both files for now (original + H.264 version)
                        # Could optionally remove original AV1 file to save space
                        return h264_path
                    else:
                        logger.warning(f"⚠️ H.264 conversion verification failed - using original")
                        if h264_path.exists():
                            h264_path.unlink()  # Clean up failed conversion
                        return video_path
                else:
                    logger.warning(f"⚠️ H.264 conversion failed - using original AV1 video")
                    return video_path
            
            # For other codecs (H.265, VP9, etc.), use original
            logger.info(f"ℹ️ Using original video with {video_codec} codec")
            return video_path
            
        except Exception as e:
            logger.error(f"❌ Preprocessing failed: {e}")
            logger.info(f"📁 Using original video: {video_path}")
            return video_path

    async def _convert_av1_to_h264_async(self, input_path: Path) -> Path:
        """
        Convert AV1 video to H.264 asynchronously during download
        Uses balanced settings (faster than processing-time conversion)
        """
        try:
            # Create H.264 version filename
            h264_filename = input_path.stem + "_h264" + input_path.suffix
            h264_path = input_path.parent / h264_filename
            
            logger.info(f"🔄 Converting AV1 to H.264 (download preprocessing)...")
            logger.info(f"   📁 Input: {input_path.name}")
            logger.info(f"   📁 Output: {h264_path.name}")
            
            # Use balanced settings: faster than high-quality but better than ultrafast
            cmd = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-i', str(input_path),
                '-c:v', 'libx264',
                '-preset', 'medium',    # Balanced speed/quality for preprocessing
                '-crf', '25',           # Good quality for processing
                '-c:a', 'copy',         # Copy audio without re-encoding
                '-movflags', '+faststart',
                '-avoid_negative_ts', 'make_zero',
                '-threads', '0',        # Use all CPU cores
                str(h264_path),
                '-y'
            ]
            
            # Allow longer timeout during download (user expects to wait)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for conversion (allow up to 10 minutes during download)
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=600.0  # 10 minutes timeout during download
                )
                
                if process.returncode == 0 and h264_path.exists():
                    file_size = h264_path.stat().st_size / (1024 * 1024)  # MB
                    logger.info(f"✅ H.264 preprocessing completed ({file_size:.1f} MB)")
                    return h264_path
                else:
                    error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                    logger.error(f"❌ H.264 preprocessing failed: {error_msg}")
                    
                    # Clean up failed file
                    if h264_path.exists():
                        h264_path.unlink()
                    return input_path
                    
            except asyncio.TimeoutError:
                logger.error(f"❌ H.264 preprocessing timed out (10 minutes)")
                logger.warning(f"⚠️ Using original AV1 video - processing may be slower")
                
                # Try to kill the process and clean up
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                    
                if h264_path.exists():
                    h264_path.unlink()
                return input_path
                
        except Exception as e:
            logger.error(f"❌ H.264 preprocessing exception: {e}")
            return input_path
    

    
    def _verify_video_codec(self, video_path: Path) -> Dict[str, str]:
        """Verify the codec of a downloaded video file"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_streams', '-select_streams', 'v:0',
                '-print_format', 'json', str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get('streams', [])
                if streams:
                    codec_name = streams[0].get('codec_name', 'unknown').lower()
                    return {
                        'codec': codec_name,
                        'width': streams[0].get('width', 0),
                        'height': streams[0].get('height', 0)
                    }
            
            return {'codec': 'unknown'}
            
        except Exception as e:
            print(f"⚠️ Could not verify codec: {e}")
            return {'codec': 'unknown'}
    


    def _extract_video_id_from_url(self, url: str) -> Dict:
        """Extract video ID from YouTube URL"""
        import re
        
        # YouTube URL patterns
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return {'id': match.group(1)}
        
        raise DownloadError(f"Could not extract video ID from URL: {url}")
    
    def _download_file_from_url(self, download_url: str, video_id: str, title: str, resolution: str) -> Path:
        """Download video file from URL and save to local filesystem"""
        try:
            # Create safe filename
            safe_title = self._sanitize_filename(title)
            filename = f"{resolution}-{safe_title}-{video_id}.mp4"
            file_path = self.downloads_dir / filename
            
            print(f"📁 Downloading to: {filename}")
            
            # Download with progress
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            if downloaded_size % (1024 * 1024) == 0:  # Log every MB
                                print(f"📥 Progress: {progress:.1f}% ({downloaded_size // (1024*1024)} MB)")
            
            if file_path.exists():
                file_size_mb = file_path.stat().st_size / (1024*1024)
                print(f"✅ Video downloaded: {file_path.name}")
                print(f"📁 File size: {file_size_mb:.1f} MB")
                return file_path.absolute()
            else:
                raise DownloadError("File was not created successfully")
                
        except requests.RequestException as e:
            raise DownloadError(f"Failed to download video file: {str(e)}")
        except Exception as e:
            raise DownloadError(f"Unexpected error during file download: {str(e)}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Create a safe filename by removing invalid characters"""
        import re
        
        # Remove emojis and special Unicode characters first
        filename = re.sub(r'[^\w\s\-\.]', '', filename, flags=re.UNICODE)
        
        # Replace spaces with underscores
        filename = re.sub(r'\s+', '_', filename)
        
        # Keep only alphanumeric, hyphens, underscores, and dots
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        
        # Remove multiple consecutive underscores
        filename = re.sub(r'_+', '_', filename)
        
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        
        # Limit length
        if len(filename) > 50:
            filename = filename[:50].rstrip('_')
        
        # Ensure filename is not empty
        if not filename:
            filename = "video"
        
        return filename



    def _find_downloaded_file(self, video_id: str, quality: Optional[str] = None) -> Optional[Path]:
        """
        Find a previously downloaded file by video_id and (optionally) quality.
        If quality is provided, look for files with that quality in the filename.
        """
        for file in self.downloads_dir.glob("*.mp4"):
            if video_id in file.name:
                if quality:
                    if quality in file.name:
                        return file
                else:
                    return file
        return None

youtube_service = YouTubeService()

# Backward compatibility functions for existing FastAPI endpoints
def get_video_id(url: str) -> str:
    """Extract video ID from YouTube URL"""
    info = youtube_service.get_video_info(url)
    return info['id']

async def download_video(url: str, quality: str = "best") -> Path:
    """
    Download video with specified quality
    Supported qualities: best, 8k, 4k, 1440p, 1080p, 720p
    """
    return await youtube_service.download_video(url, quality)

def get_video_info(url: str) -> Dict:
    """Get detailed video information"""
    return youtube_service.get_video_info(url)

def get_available_formats(url: str) -> List[Dict]:
    """Get available video formats"""
    return youtube_service.get_available_formats(url)

def cut_clips(video_path: Path, analysis: Dict) -> List[Path]:
    """
    Cut clips from video based on Gemini analysis using MoviePy 2.2.1 API.
    analysis comes from gemini.py and has structure:
    {
      "gemini_analysis": {
        "viral_segments": [
          {
            "title": "...",
            "start": 85,
            "end": 129,
            "duration": 44,
            "subtitles": {...}
          }
        ]
      }
    }
    """
    clips_dir = Path("clips")
    clips_dir.mkdir(exist_ok=True)
    
    # Extract viral segments from analysis
    gemini_analysis = analysis.get("gemini_analysis", {})
    viral_segments = gemini_analysis.get("viral_segments", [])
    
    if not viral_segments:
        logging.warning("No viral segments found in analysis")
        return []
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    print(f"✂️ Нарезаю {len(viral_segments)} клипов из {video_path.name}")
    
    # Load video with MoviePy 2.2.1
    try:
        video = VideoFileClip(str(video_path))
        video_duration = video.duration
        print(f"📹 Длительность видео: {video_duration:.1f} сек")
    except Exception as e:
        raise Exception(f"Failed to load video with MoviePy: {str(e)}")
    
    created_clips = []
    skipped_clips = []
    failed_clips = []
    
    for i, segment in enumerate(viral_segments):
        clip_id = i + 1
        title = segment.get('title', f'Segment_{clip_id}')
        start = segment.get('start', 0)
        end = segment.get('end', start + 60)  # Default 60 sec if no end
        
        print(f"\n--- Клип {clip_id}: {title} ---")
        print(f"⏰ Время: {start} - {end} сек ({end - start} сек)")
        
        # Enhanced validation with detailed logging
        if start >= end:
            reason = f"Invalid timing: start ({start}) >= end ({end})"
            print(f"⚠️ ПРОПУСКАЮ клип {clip_id}: {reason}")
            skipped_clips.append({"clip_id": clip_id, "title": title, "reason": reason})
            continue
            
        if start < 0:
            reason = f"Invalid start time: {start} < 0"
            print(f"⚠️ ПРОПУСКАЮ клип {clip_id}: {reason}")
            skipped_clips.append({"clip_id": clip_id, "title": title, "reason": reason})
            continue
            
        if end > video_duration:
            # Adjust end time instead of skipping
            original_end = end
            end = video_duration
            print(f"⚠️ КОРРЕКТИРУЮ клип {clip_id}: end {original_end} -> {end} (video duration)")
        
        try:
            # Create safe filename
            safe_title = youtube_service._sanitize_filename(title)
            clip_filename = f"{clip_id:02d}_{safe_title}.mp4"
            clip_path = clips_dir / clip_filename
            
            print(f"📁 Сохраняю как: {clip_filename}")
            
            # Cut segment with MoviePy 2.2.1 API
            print(f"✂️ Нарезаю сегмент {start:.1f}-{end:.1f}...")
            try:
                segment_clip = video.subclipped(start, end)
            except Exception as e:
                if "'NoneType' object has no attribute 'stdout'" in str(e):
                    print(f"⚠️ MoviePy subclip failed for clip {clip_id}, trying direct ffmpeg fallback...")
                    
                    # Try direct ffmpeg approach without MoviePy
                    if create_clip_with_direct_ffmpeg(video_path, start, end, clip_path):
                        if clip_path.exists():
                            file_size = clip_path.stat().st_size
                            if file_size > 0:
                                file_size_mb = file_size / (1024*1024)
                                print(f"✅ Клип создан (via direct ffmpeg): {clip_path.name} ({file_size_mb:.1f} MB)")
                                created_clips.append(clip_path.absolute())
                                continue
                            else:
                                clip_path.unlink()  # Delete empty file
                    
                    reason = f"Both MoviePy subclip and direct ffmpeg failed: {str(e)}"
                    print(f"❌ ОШИБКА клип {clip_id}: {reason}")
                    failed_clips.append({"clip_id": clip_id, "title": title, "reason": reason})
                    continue
                else:
                    raise e
            
            # Write video file with MAXIMUM QUALITY settings
            print(f"💾 Записываю видеофайл с максимальным качеством...")
            try:
                segment_clip.write_videofile(
                    str(clip_path),
                    codec='libx264',
                    audio_codec='aac',
                    # High quality settings
                    ffmpeg_params=[
                        '-crf', '18',        # Visually lossless quality
                        '-preset', 'slow',   # Better compression efficiency
                        '-profile:v', 'high', # H.264 high profile for better quality
                        '-level', '4.0',     # H.264 level for compatibility
                        '-pix_fmt', 'yuv420p', # Standard pixel format for compatibility
                        '-movflags', '+faststart', # Fast start for web playback
                        '-b:a', '192k'       # High audio bitrate
                    ],
                    logger=None
                )
            except Exception as e:
                if "'NoneType' object has no attribute 'stdout'" in str(e):
                    print(f"⚠️ MoviePy failed for clip {clip_id}, trying direct ffmpeg fallback...")
                    segment_clip.close()
                    
                    # Try direct ffmpeg approach
                    if create_clip_with_direct_ffmpeg(video_path, start, end, clip_path):
                        if clip_path.exists():
                            file_size = clip_path.stat().st_size
                            if file_size > 0:
                                file_size_mb = file_size / (1024*1024)
                                print(f"✅ Клип создан (via direct ffmpeg): {clip_path.name} ({file_size_mb:.1f} MB)")
                                created_clips.append(clip_path.absolute())
                                continue
                            else:
                                clip_path.unlink()  # Delete empty file
                    
                    reason = f"Both MoviePy and direct ffmpeg failed: {str(e)}"
                    print(f"❌ ОШИБКА клип {clip_id}: {reason}")
                    failed_clips.append({"clip_id": clip_id, "title": title, "reason": reason})
                    continue
                else:
                    raise e
            
            # Close clip to free memory
            segment_clip.close()
            
            # Verify file creation and size
            if clip_path.exists():
                file_size = clip_path.stat().st_size
                if file_size == 0:
                    reason = "Generated file is empty (0 bytes)"
                    print(f"❌ ОШИБКА клип {clip_id}: {reason}")
                    clip_path.unlink()  # Delete empty file
                    failed_clips.append({"clip_id": clip_id, "title": title, "reason": reason})
                else:
                    file_size_mb = file_size / (1024*1024)
                    print(f"✅ Клип создан: {clip_path.name} ({file_size_mb:.1f} MB)")
                    created_clips.append(clip_path.absolute())
            else:
                reason = "File was not created by MoviePy"
                print(f"❌ ОШИБКА клип {clip_id}: {reason}")
                failed_clips.append({"clip_id": clip_id, "title": title, "reason": reason})
                
        except Exception as e:
            reason = f"Exception during processing: {str(e)}"
            print(f"❌ ОШИБКА клип {clip_id}: {reason}")
            failed_clips.append({"clip_id": clip_id, "title": title, "reason": reason})
            
            # Try to clean up any partial files
            if 'clip_path' in locals() and clip_path.exists():
                try:
                    clip_path.unlink()
                    print(f"🧹 Удален частичный файл: {clip_path.name}")
                except:
                    pass
            continue
    
    # Close main video
    video.close()
    
    # Detailed summary
    print(f"\n🎉 РЕЗУЛЬТАТ НАРЕЗКИ:")
    print(f"✅ Создано клипов: {len(created_clips)}")
    print(f"⚠️ Пропущено клипов: {len(skipped_clips)}")
    print(f"❌ Ошибок при создании: {len(failed_clips)}")
    print(f"📊 Общий итог: {len(created_clips)}/{len(viral_segments)}")
    
    # Log details of skipped/failed clips
    if skipped_clips:
        print(f"\n⚠️ ПРОПУЩЕННЫЕ КЛИПЫ:")
        for skip in skipped_clips:
            print(f"  - Клип {skip['clip_id']} ({skip['title']}): {skip['reason']}")
    
    if failed_clips:
        print(f"\n❌ НЕУДАЧНЫЕ КЛИПЫ:")
        for fail in failed_clips:
            print(f"  - Клип {fail['clip_id']} ({fail['title']}): {fail['reason']}")
    
    return created_clips


def cut_clips_vertical(video_path: Path, analysis: Dict, smoothing_strength: str = "very_high") -> List[Path]:
    """
    Cuts a video into vertical clips based on analysis, with motion smoothing.

    Args:
        video_path: Path to the source video file.
        analysis: Dictionary containing viral segments from Gemini.
        smoothing_strength: Motion smoothing level.
    
    Returns:
        A list of paths to the created vertical clips.
    """
    if not VERTICAL_CROP_AVAILABLE:
        print("❌ Vertical cropping service not available, cannot create vertical clips")
        return []
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return []
    
    viral_segments = analysis.get("gemini_analysis", {}).get("viral_segments", [])
    if not viral_segments:
        print("❌ No viral segments found in analysis")
        return []
        
    clips_dir = Path("clips") / "vertical"
    clips_dir.mkdir(parents=True, exist_ok=True)
    
    created_clips = []
    
    print(f"\n📱 Creating {len(viral_segments)} vertical clips...")
    
    for i, segment in enumerate(viral_segments):
        start_time = segment.get("start")
        end_time = segment.get("end")
        
        if start_time is None or end_time is None:
            continue

        base_name = youtube_service._sanitize_filename(segment.get("title", f"segment_{i+1}"))
        
        # Create a temporary horizontal clip first
        temp_horizontal_clip_path = clips_dir / f"temp_{base_name}.mp4"
        
        try:
            print(f"  ➡️  Step 1/2: Cutting horizontal segment: '{base_name}' ({start_time}-{end_time})")
            
            # Use direct ffmpeg for robust cutting
            success = create_clip_with_direct_ffmpeg(
                video_path, start_time, end_time, temp_horizontal_clip_path
            )

            if not success or not temp_horizontal_clip_path.exists():
                print(f"      ❌ Failed to cut horizontal segment")
                continue

            # Now, create vertical crop from the temporary clip
            vertical_clip_path = clips_dir / f"{base_name}_vertical.mp4"
            print(f"  🔄  Step 2/2: Converting to vertical format...")

            crop_success = crop_video_to_vertical(
                input_path=temp_horizontal_clip_path,
                output_path=vertical_clip_path,
                use_speaker_detection=True,
                smoothing_strength=smoothing_strength
            )

            if crop_success:
                print(f"      ✅ Vertical clip created: {vertical_clip_path.name}")
                created_clips.append(vertical_clip_path)
            else:
                print(f"      ❌ Failed to create vertical crop for '{base_name}'")

        except Exception as e:
            print(f"  ❌ Error processing segment '{base_name}': {e}")
        
        finally:
            # Clean up the temporary horizontal clip
            if temp_horizontal_clip_path.exists():
                os.remove(temp_horizontal_clip_path)

    print(f"\n✅ Vertical clip creation complete: {len(created_clips)} clips created.")
    return created_clips


def check_video_quality(video_path: Path) -> Dict:
    """
    Быстрая проверка качества скачанного видео
    Возвращает основную информацию о качестве
    """
    try:
        from moviepy import VideoFileClip
        
        if not video_path.exists():
            return {"error": f"Файл не найден: {video_path}"}
        
        # Получить базовую информацию
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        
        # Попробовать загрузить видео с MoviePy
        try:
            with VideoFileClip(str(video_path)) as video:
                width, height = video.size
                duration = video.duration
                fps = video.fps
                
                # Определить качество
                if height >= 4320:
                    quality_level = "8K Ultra"
                elif height >= 2160:
                    quality_level = "4K Very High"
                elif height >= 1440:
                    quality_level = "2K High"
                elif height >= 1080:
                    quality_level = "Full HD"
                elif height >= 720:
                    quality_level = "HD"
                else:
                    quality_level = "Low"
                
                return {
                    "file_name": video_path.name,
                    "file_size_mb": round(file_size_mb, 1),
                    "resolution": f"{width}x{height}",
                    "quality_level": quality_level,
                    "duration_minutes": round(duration / 60, 1),
                    "fps": round(fps, 1) if fps else "N/A",
                    "mb_per_minute": round(file_size_mb / (duration / 60), 1) if duration > 0 else 0,
                    "status": "success"
                }
        except Exception as e:
            return {
                "error": f"Ошибка при анализе видео: {str(e)}",
                "file_name": video_path.name,
                "file_size_mb": round(file_size_mb, 1)
            }
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

 

async def cut_clips_vertical_async(video_path: Path, analysis: Dict, smoothing_strength: str = "very_high") -> List[Path]:
    """
    Async version of cut_clips_vertical that uses the AsyncVerticalCropService for concurrent processing.
    
    Args:
        video_path: Path to the source video file.
        analysis: Dictionary containing viral segments from Gemini.
        smoothing_strength: Motion smoothing level.
    
    Returns:
        A list of paths to the created vertical clips.
    """
    from app.services.vertical_crop_async import async_vertical_crop_service
    
    # Create output directory for clips
    clips_dir = Path("clips")
    clips_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract viral segments
    gemini_analysis = analysis.get("gemini_analysis", {})
    viral_segments = gemini_analysis.get("viral_segments", [])
    
    if not viral_segments:
        logging.warning("No viral segments found in analysis")
        return []
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    print(f"✂️ 🔥 Создаю {len(viral_segments)} вертикальных клипов АСИНХРОННО из {video_path.name}")
    
    # First, cut the horizontal clips
    horizontal_clips = cut_clips(video_path, analysis)
    
    if not horizontal_clips:
        print("❌ Не удалось создать горизонтальные клипы")
        return []
    
    print(f"📹 Создано {len(horizontal_clips)} горизонтальных клипов, теперь делаю их вертикальными...")
    
    # Start async vertical cropping tasks for all clips
    crop_tasks = []
    vertical_clip_paths = []
    
    for i, horizontal_clip_path in enumerate(horizontal_clips):
        if not horizontal_clip_path.exists():
            print(f"⚠️ Горизонтальный клип не найден: {horizontal_clip_path}")
            continue
        
        # Generate vertical clip path
        vertical_clip_path = clips_dir / f"{horizontal_clip_path.stem}_vertical.mp4"
        vertical_clip_paths.append(vertical_clip_path)
        
        print(f"🚀 Запускаю вертикальную обрезку {i+1}/{len(horizontal_clips)}: {horizontal_clip_path.name}")
        
        # Start async vertical crop task
        task = async_vertical_crop_service.create_vertical_crop_async(
            input_video_path=horizontal_clip_path,
            output_video_path=vertical_clip_path,
            use_speaker_detection=True,
            smoothing_strength=smoothing_strength
        )
        crop_tasks.append(task)
    
    if not crop_tasks:
        print("❌ Не удалось запустить задачи вертикальной обрезки")
        return []
    
    print(f"⏳ Ожидаю завершения {len(crop_tasks)} задач вертикальной обрезки...")
    
    # Wait for all crop tasks to complete
    try:
        results = await asyncio.gather(*crop_tasks, return_exceptions=True)
        
        successful_clips = []
        failed_clips = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Ошибка при обрезке клипа {i+1}: {str(result)}")
                failed_clips += 1
            elif isinstance(result, dict) and result.get("success"):
                output_path = Path(result["output_path"])
                if output_path.exists():
                    successful_clips.append(output_path)
                    print(f"✅ Вертикальный клип создан: {output_path.name}")
                else:
                    print(f"⚠️ Клип успешно обработан, но файл не найден: {output_path}")
                    failed_clips += 1
            else:
                print(f"❌ Неудачная обрезка клипа {i+1}: {result.get('error', 'Unknown error')}")
                failed_clips += 1
        
        print(f"\n🎉 РЕЗУЛЬТАТ ВЕРТИКАЛЬНОЙ НАРЕЗКИ:")
        print(f"✅ Создано вертикальных клипов: {len(successful_clips)}")
        print(f"❌ Неудачных обрезок: {failed_clips}")
        print(f"📊 Итого: {len(successful_clips)}/{len(crop_tasks)}")
        
        # Clean up horizontal clips (optional)
        print(f"🧹 Очищаю промежуточные горизонтальные клипы...")
        for horizontal_clip in horizontal_clips:
            try:
                if horizontal_clip.exists():
                    horizontal_clip.unlink()
                    print(f"  🗑️ Удален: {horizontal_clip.name}")
            except Exception as e:
                print(f"  ⚠️ Не удалось удалить {horizontal_clip.name}: {e}")
        
        return successful_clips
        
    except Exception as e:
        print(f"❌ Критическая ошибка при асинхронной обрезке: {str(e)}")
        return [] 

def extract_frames_with_ffmpeg(video_path: str, output_dir: str = "frames", cleanup: bool = True):
    """
    Extract frames from a video using FFmpeg (as PNGs), yield them as OpenCV images.
    Cleans up the frames after processing if cleanup=True.
    """
    import cv2
    import glob
    import os
    import subprocess

    # Ensure output directory exists and is empty
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Extract frames as PNGs
    ffmpeg_cmd = [
        'ffmpeg', '-i', str(video_path), f'{output_dir}/frame_%06d.png', '-hide_banner', '-loglevel', 'error'
    ]
    subprocess.run(ffmpeg_cmd, check=True)

    # Yield frames as OpenCV images
    frame_files = sorted(glob.glob(f'{output_dir}/frame_*.png'))
    for frame_file in frame_files:
        frame = cv2.imread(frame_file)
        yield frame

    # Cleanup
    if cleanup:
        shutil.rmtree(output_dir) 