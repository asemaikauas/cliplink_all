"""
FFmpeg-based video processor for maximum quality preservation
Replaces OpenCV video operations while maintaining MediaPipe face detection
"""

import asyncio
import cv2
import numpy as np
import tempfile
import shutil
import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Generator
import subprocess
import uuid
import mediapipe as mp

logger = logging.getLogger(__name__)

class FFmpegVideoProcessor:
    """
    High-quality video processor using FFmpeg for I/O and MediaPipe for face detection
    Replaces OpenCV video operations for superior quality preservation
    """
    
    def __init__(self):
        # Initialize MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detector = self.mp_face_detection.FaceDetection(
            model_selection=1,  # 1 for videos (better range)
            min_detection_confidence=0.3  # Lower threshold for better detection
        )
        logger.info("✅ FFmpeg Video Processor with MediaPipe face detection initialized")
    
    async def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get detailed video information using FFprobe"""
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', 
            '-show_streams', str(video_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"FFprobe failed: {stderr.decode()}")
        
        data = json.loads(stdout.decode())
        
        # Extract video stream info
        video_stream = None
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                video_stream = stream
                break
        
        if not video_stream:
            raise Exception("No video stream found")
        
        return {
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'fps': eval(video_stream['r_frame_rate']),  # Convert fraction to float
            'duration': float(video_stream.get('duration', 0)),
            'codec': video_stream['codec_name'],
            'bitrate': int(video_stream.get('bit_rate', 0)),
            'frames': int(video_stream.get('nb_frames', 0))
        }
    
    async def extract_frames_high_quality(
        self, 
        video_path: Path, 
        output_dir: Path,
        quality: str = "lossless"
    ) -> List[Path]:
        """
        Extract frames using FFmpeg with maximum quality preservation
        
        Args:
            video_path: Input video file
            output_dir: Directory to store extracted frames
            quality: 'lossless', 'high', 'medium', 'fast'
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Quality settings for frame extraction
        quality_settings = {
            'lossless': ['-q:v', '1'],  # Highest quality
            'high': ['-q:v', '2'],      # High quality  
            'medium': ['-q:v', '5'],    # Medium quality
            'fast': ['-q:v', '10']      # Fast extraction
        }
        
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-hide_banner', '-loglevel', 'error',
            *quality_settings.get(quality, quality_settings['high']),
            '-pix_fmt', 'rgb24',  # Consistent pixel format
            str(output_dir / 'frame_%06d.png')
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Frame extraction failed: {stderr.decode()}")
        
        # Return sorted list of extracted frames
        frame_files = sorted(list(output_dir.glob('frame_*.png')))
        logger.info(f"✅ Extracted {len(frame_files)} frames with {quality} quality")
        return frame_files
    
    def detect_faces_in_frame(self, frame_path: Path) -> List[Tuple[int, int, int, int]]:
        """Detect faces in a single frame using MediaPipe"""
        frame = cv2.imread(str(frame_path))
        if frame is None:
            return []
        
        try:
            h, w = frame.shape[:2]
            
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame with MediaPipe
            results = self.face_detector.process(rgb_frame)
            
            faces = []
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    
                    # Convert to absolute coordinates
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    x1 = int((bbox.xmin + bbox.width) * w)
                    y1 = int((bbox.ymin + bbox.height) * h)
                    
                    # Ensure coordinates are valid
                    x = max(0, min(w, x))
                    y = max(0, min(h, y))
                    x1 = max(0, min(w, x1))
                    y1 = max(0, min(h, y1))
                    
                    if x1 > x and y1 > y:
                        faces.append((x, y, x1, y1))
            
            return faces
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []
    
    async def crop_frame_to_vertical(
        self, 
        frame_path: Path, 
        output_path: Path, 
        faces: List[Tuple[int, int, int, int]],
        target_size: Tuple[int, int] = (608, 1080),
        crop_position: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Crop frame to vertical format using FFmpeg for maximum quality
        
        Args:
            frame_path: Input frame file
            output_path: Output cropped frame
            faces: List of face bounding boxes from MediaPipe
            target_size: Target dimensions (width, height)
            crop_position: Override crop center position
        """
        try:
            # Read frame to get dimensions
            frame = cv2.imread(str(frame_path))
            h, w = frame.shape[:2]
            target_width, target_height = target_size
            
            # Determine crop center
            if crop_position:
                crop_x, crop_y = crop_position
            elif faces:
                # Use first detected face
                x, y, x1, y1 = faces[0]
                crop_x = (x + x1) // 2
                crop_y = (y + y1) // 2
            else:
                # Center crop (better than the old 75% right fallback!)
                crop_x = w // 2
                crop_y = h // 2
            
            # Calculate crop dimensions maintaining aspect ratio
            if w / h > target_width / target_height:
                # Wide video - fit height, crop width
                crop_height = h
                crop_width = int(h * target_width / target_height)
            else:
                # Tall video - fit width, crop height  
                crop_width = w
                crop_height = int(w * target_height / target_width)
            
            # Calculate crop coordinates
            left = max(0, crop_x - crop_width // 2)
            top = max(0, crop_y - crop_height // 2)
            
            # Adjust if crop exceeds boundaries
            if left + crop_width > w:
                left = w - crop_width
            if top + crop_height > h:
                top = h - crop_height
            
            # Use FFmpeg for high-quality cropping and scaling
            cmd = [
                'ffmpeg', '-i', str(frame_path),
                '-hide_banner', '-loglevel', 'error',
                '-vf', f'crop={crop_width}:{crop_height}:{left}:{top},scale={target_width}:{target_height}:flags=lanczos',
                '-q:v', '1',  # Highest quality
                '-y', str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                logger.error(f"Frame cropping failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error cropping frame: {e}")
            return False
    
    async def reconstruct_video_ultra_quality(
        self,
        frame_dir: Path,
        output_video: Path,
        fps: float,
        audio_path: Optional[Path] = None,
        quality_preset: str = "ultra"
    ) -> bool:
        """
        Reconstruct video from frames using FFmpeg with ultra-high quality settings
        
        Args:
            frame_dir: Directory containing processed frames
            output_video: Output video file
            fps: Frames per second
            audio_path: Optional audio file to merge
            quality_preset: 'ultra', 'high', 'balanced', 'fast'
        """
        try:
            # Ultra-high quality encoding presets
            quality_presets = {
                'ultra': {
                    'crf': '15',           # Near-lossless quality
                    'preset': 'slower',    # Best compression efficiency
                    'profile': 'high',     # H.264 high profile
                    'level': '4.2',        # Support 4K
                    'pix_fmt': 'yuv420p',  # Standard compatibility
                    'extra': ['-tune', 'film', '-movflags', '+faststart']
                },
                'high': {
                    'crf': '18',           # Visually lossless
                    'preset': 'slow',      # Good compression
                    'profile': 'high',
                    'level': '4.1',
                    'pix_fmt': 'yuv420p',
                    'extra': ['-movflags', '+faststart']
                },
                'balanced': {
                    'crf': '21',           # High quality
                    'preset': 'medium',    # Balanced speed/quality
                    'profile': 'main',
                    'level': '4.0',
                    'pix_fmt': 'yuv420p',
                    'extra': ['-movflags', '+faststart']
                },
                'fast': {
                    'crf': '23',           # Good quality
                    'preset': 'fast',      # Fast encoding
                    'profile': 'main',
                    'level': '3.1',
                    'pix_fmt': 'yuv420p',
                    'extra': []
                }
            }
            
            preset = quality_presets.get(quality_preset, quality_presets['high'])
            
            # Base command for video reconstruction
            cmd = [
                'ffmpeg',
                '-hide_banner', '-loglevel', 'error',
                '-framerate', str(fps),
                '-i', str(frame_dir / 'frame_%06d.png'),
            ]
            
            # Add audio if available
            if audio_path and audio_path.exists():
                cmd.extend(['-i', str(audio_path)])
                cmd.extend(['-c:a', 'aac', '-b:a', '256k', '-ar', '48000'])  # High-quality audio
            
            # Add video encoding settings
            cmd.extend([
                '-c:v', 'libx264',
                '-crf', preset['crf'],
                '-preset', preset['preset'],
                '-profile:v', preset['profile'],
                '-level', preset['level'],
                '-pix_fmt', preset['pix_fmt'],
                *preset['extra'],
                '-y', str(output_video)
            ])
            
            logger.info(f"🎬 Reconstructing video with {quality_preset} quality (CRF {preset['crf']})")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ Video reconstruction completed: {output_video}")
                return True
            else:
                logger.error(f"❌ Video reconstruction failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error reconstructing video: {e}")
            return False
    
    async def process_video_to_vertical_ultra_quality(
        self,
        input_video: Path,
        output_video: Path,
        target_size: Tuple[int, int] = (608, 1080),
        quality_preset: str = "ultra",
        use_face_detection: bool = True
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Video → Frames → Face Detection → Crop → Reconstruct
        Using FFmpeg for maximum quality preservation
        """
        temp_dir = None
        try:
            # Create temporary directory for frames
            temp_dir = Path(tempfile.mkdtemp(prefix="ffmpeg_processing_"))
            frames_dir = temp_dir / "frames"
            cropped_dir = temp_dir / "cropped"
            cropped_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"🚀 Starting ultra-quality video processing: {input_video}")
            
            # Step 1: Get video info
            video_info = await self.get_video_info(input_video)
            logger.info(f"📹 Video: {video_info['width']}x{video_info['height']}, {video_info['fps']} fps, {video_info['codec']}")
            
            # Step 2: Extract frames with maximum quality
            frame_files = await self.extract_frames_high_quality(input_video, frames_dir, "lossless")
            logger.info(f"📸 Extracted {len(frame_files)} frames")
            
            # Step 3: Process each frame (face detection + cropping)
            processed_frames = 0
            previous_crop_center = None
            
            for frame_file in frame_files:
                frame_number = int(frame_file.stem.split('_')[1])
                output_frame = cropped_dir / f"frame_{frame_number:06d}.png"
                
                # Detect faces if enabled
                faces = []
                if use_face_detection:
                    faces = self.detect_faces_in_frame(frame_file)
                
                # Crop frame to vertical format
                success = await self.crop_frame_to_vertical(
                    frame_file, output_frame, faces, target_size, previous_crop_center
                )
                
                if success:
                    processed_frames += 1
                    # Update crop center for smoothing (basic implementation)
                    if faces:
                        x, y, x1, y1 = faces[0]
                        previous_crop_center = ((x + x1) // 2, (y + y1) // 2)
                else:
                    logger.warning(f"Failed to process frame {frame_number}")
            
            logger.info(f"✅ Processed {processed_frames}/{len(frame_files)} frames")
            
            # Step 4: Reconstruct video with ultra quality
            success = await self.reconstruct_video_ultra_quality(
                cropped_dir, output_video, video_info['fps'], 
                quality_preset=quality_preset
            )
            
            if success:
                result = {
                    'success': True,
                    'output_path': str(output_video),
                    'original_resolution': f"{video_info['width']}x{video_info['height']}",
                    'target_resolution': f"{target_size[0]}x{target_size[1]}",
                    'frames_processed': processed_frames,
                    'quality_preset': quality_preset,
                    'face_detection_used': use_face_detection,
                    'codec': video_info['codec']
                }
                logger.info(f"🎉 Ultra-quality processing completed successfully!")
                return result
            else:
                raise Exception("Video reconstruction failed")
                
        except Exception as e:
            logger.error(f"❌ Ultra-quality processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # Cleanup temporary files
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info("🧹 Temporary files cleaned up")

# Global instance
ffmpeg_processor = FFmpegVideoProcessor() 