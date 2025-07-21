"""
Asynchronous vertical cropping service for creating YouTube Shorts (9:16 aspect ratio)
Designed to handle multiple concurrent requests without blocking
"""

import asyncio
import cv2
import numpy as np
import os
import logging
import uuid
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import webrtcvad
import wave
import contextlib
from pydub import AudioSegment
from moviepy import VideoFileClip, AudioFileClip
import subprocess
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime
import threading
import json
import tempfile

# Smart Scene detection imports for intelligent crop reset
try:
    from scenedetect import VideoManager, SceneManager
    from scenedetect.detectors import ContentDetector, ThresholdDetector
    SCENEDETECT_AVAILABLE = True
    logging.info("✅ PySceneDetect available for smart scene detection")
except ImportError:
    SCENEDETECT_AVAILABLE = False
    logging.warning("⚠️ PySceneDetect not available. Smart scene detection disabled.")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncVerticalCropService:
    """
    Asynchronous service for creating vertical (9:16) crops of videos with intelligent speaker tracking
    Supports concurrent processing of multiple requests
    """
    
    def __init__(self, max_workers: int = 4, max_concurrent_tasks: int = 10):
        # Thread pool for CPU-intensive tasks
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Process pool for very heavy operations
        self.process_executor = ProcessPoolExecutor(max_workers=min(4, max_workers))
        
        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_lock = threading.Lock()
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # Initialize VAD for voice activity detection
        try:
            self.vad = webrtcvad.Vad(2)  # Aggressiveness mode 0-3
            logger.info("✅ Voice Activity Detection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize VAD: {e}")
            self.vad = None
        
        # Try to load OpenCV DNN model for face detection
        self.face_net = self._load_face_detection_model()
        
        logger.info(f"🚀 AsyncVerticalCropService initialized with {max_workers} workers, max {max_concurrent_tasks} concurrent tasks")
    
    def _load_face_detection_model(self):
        """Load OpenCV DNN model for face detection (thread-safe)"""
        try:
            prototxt_path = "models/deploy.prototxt"
            model_path = "models/res10_300x300_ssd_iter_140000_fp16.caffemodel"
            
            if Path(prototxt_path).exists() and Path(model_path).exists():
                net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
                logger.info("✅ Face detection model loaded")
                return net
            else:
                logger.warning("⚠️ Face detection models not found. Using center-crop fallback.")
                return None
        except Exception as e:
            logger.warning(f"⚠️ Could not load face detection model: {e}")
            return None
    
    async def _run_cpu_bound_task(self, func, *args, **kwargs):
        """Run CPU-bound task in thread executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_executor, func, *args, **kwargs)
    
    async def _run_heavy_task(self, func, *args, **kwargs):
        """Run very heavy task in process executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.process_executor, func, *args, **kwargs)
    
    def _create_task_id(self) -> str:
        """Generate unique task ID"""
        return f"crop_{uuid.uuid4().hex[:8]}"
    
    def _update_task_status(self, task_id: str, status: str, progress: int = 0, message: str = "", data: Optional[Dict] = None):
        """Thread-safe task status update"""
        with self.task_lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id].update({
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "updated_at": datetime.now().isoformat()
                })
                if data:
                    self.active_tasks[task_id].update(data)
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID"""
        with self.task_lock:
            return self.active_tasks.get(task_id, None)
    
    async def list_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """List all active tasks"""
        with self.task_lock:
            return self.active_tasks.copy()
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self.task_lock:
            tasks_to_remove = []
            for task_id, task_info in self.active_tasks.items():
                if task_info.get("status") in ["completed", "failed"]:
                    created_time = task_info.get("created_at", datetime.now()).timestamp()
                    if created_time < cutoff_time:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.active_tasks[task_id]
            
            logger.info(f"🧹 Cleaned up {len(tasks_to_remove)} old tasks")
    
    def _detect_faces_sync(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Synchronous face detection for thread executor"""
        if self.face_net is None:
            return []
        
        try:
            h, w = frame.shape[:2]
            blob = cv2.dnn.blobFromImage(
                cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
            )
            self.face_net.setInput(blob)
            detections = self.face_net.forward()
            
            faces = []
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > 0.5:
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    
                    # Check for invalid values before casting
                    if np.any(np.isnan(box)) or np.any(np.isinf(box)):
                        continue
                    
                    x, y, x1, y1 = box.astype("int")
                    
                    # Ensure coordinates are within frame bounds
                    x = max(0, min(w, x))
                    y = max(0, min(h, y))
                    x1 = max(0, min(w, x1))
                    y1 = max(0, min(h, y1))
                    
                    # Ensure valid bounding box (x1 > x and y1 > y)
                    if x1 > x and y1 > y:
                        faces.append((x, y, x1, y1))
            
            return faces
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []
    
    async def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Async face detection"""
        return await self._run_cpu_bound_task(self._detect_faces_sync, frame)
    
    def _detect_voice_activity_sync(self, audio_frame: bytes) -> bool:
        """Synchronous voice activity detection"""
        if self.vad is None:
            return True
        
        try:
            return self.vad.is_speech(audio_frame, 16000)
        except Exception as e:
            logger.error(f"Voice activity detection error: {e}")
            return True
    
    async def detect_voice_activity(self, audio_frame: bytes) -> bool:
        """Async voice activity detection"""
        return await self._run_cpu_bound_task(self._detect_voice_activity_sync, audio_frame)
    
    async def find_active_speaker(
        self, 
        frame: np.ndarray, 
        audio_frame: Optional[bytes] = None,
        previous_crop_center: Optional[Tuple[int, int]] = None,
        enable_dual_speaker_mode: bool = False
    ) -> Optional[Tuple[int, int, int, int]] | Dict[str, Any]:
        """
        Async active speaker detection with optional dual-speaker mode
        
        Returns:
            - Single speaker mode: Tuple of (x, y, x1, y1) for best face or None
            - Dual speaker mode: Dict with 'mode' and 'speakers' keys for 2 faces, or single tuple for 1 face
        """
        faces = await self.detect_faces(frame)
        
        if not faces:
            return None
        
        if len(faces) == 1:
            return faces[0]
        
        # 👥 DUAL SPEAKER MODE: When exactly 2 faces detected and mode enabled
        if len(faces) == 2 and enable_dual_speaker_mode:
            h, w = frame.shape[:2]
            
            # Sort faces by horizontal position (left to right)
            faces_sorted = sorted(faces, key=lambda face: (face[0] + face[2]) / 2)
            
            # Check voice activity
            has_voice_activity = True
            if audio_frame:
                has_voice_activity = await self.detect_voice_activity(audio_frame)
            
            return {
                "mode": "dual_speaker",
                "speaker_1": faces_sorted[0],  # Left/first speaker
                "speaker_2": faces_sorted[1],  # Right/second speaker  
                "has_voice": has_voice_activity,
                "frame_size": (w, h)
            }
        
        # Multiple faces (>2): use original heuristics to pick best single speaker
        h, w = frame.shape[:2]
        best_face = None
        best_score = 0
        
        # Check voice activity
        has_voice_activity = True
        if audio_frame:
            has_voice_activity = await self.detect_voice_activity(audio_frame)
        
        for face in faces:
            x, y, x1, y1 = face
            face_width = x1 - x
            face_height = y1 - y
            
            # Score calculations
            size_score = (face_width * face_height) / (w * h)
            
            face_center_x = (x + x1) / 2
            face_center_y = (y + y1) / 2
            center_score = 1.0 - (abs(face_center_x - w/2) / (w/2))
            
            # Stability score
            stability_score = 0
            if previous_crop_center:
                prev_x, prev_y = previous_crop_center
                distance = np.sqrt((face_center_x - prev_x)**2 + (face_center_y - prev_y)**2)
                max_distance = np.sqrt(w**2 + h**2) / 3
                stability_score = max(0, 1.0 - distance / max_distance)
            
            total_score = (
                size_score * 0.35 + 
                center_score * 0.25 + 
                stability_score * 0.4
            )
            
            if has_voice_activity:
                total_score *= 1.15
            
            if total_score > best_score:
                best_score = total_score
                best_face = face
        
        return best_face
    
    def _smooth_crop_center(
        self, 
        new_center: Tuple[int, int], 
        previous_crop_center: Optional[Tuple[int, int]],
        recent_centers: List[Tuple[int, int]],
        smoothing_config: Dict[str, Any]
    ) -> Tuple[Tuple[int, int], List[Tuple[int, int]]]:
        """Smooth crop center calculation"""
        smoothing_factor = smoothing_config["smoothing_factor"]
        max_jump_distance = smoothing_config["max_jump_distance"]
        stability_frames = smoothing_config["stability_frames"]
        
        if previous_crop_center is None:
            return new_center, [new_center]
        
        # Add new center to history
        recent_centers = recent_centers.copy()
        recent_centers.append(new_center)
        if len(recent_centers) > stability_frames:
            recent_centers.pop(0)
        
        # Calculate average
        avg_x = sum(center[0] for center in recent_centers) / len(recent_centers)
        avg_y = sum(center[1] for center in recent_centers) / len(recent_centers)
        averaged_center = (int(avg_x), int(avg_y))
        
        prev_x, prev_y = previous_crop_center
        new_x, new_y = averaged_center
        
        # Limit jump distance
        distance = np.sqrt((new_x - prev_x)**2 + (new_y - prev_y)**2)
        
        if distance > max_jump_distance:
            direction_x = (new_x - prev_x) / distance if distance > 0 else 0
            direction_y = (new_y - prev_y) / distance if distance > 0 else 0
            
            new_x = prev_x + direction_x * max_jump_distance
            new_y = prev_y + direction_y * max_jump_distance
        
        # Apply exponential smoothing
        smoothed_x = int(prev_x * smoothing_factor + new_x * (1 - smoothing_factor))
        smoothed_y = int(prev_y * smoothing_factor + new_y * (1 - smoothing_factor))
        
        return (smoothed_x, smoothed_y), recent_centers
    
    def _crop_frame_to_vertical(
        self, 
        frame: np.ndarray, 
        speaker_box: Optional[Tuple[int, int, int, int]],
        target_size: Tuple[int, int],
        crop_center: Optional[Tuple[int, int]] = None,
        padding_factor: float = 1.5
    ) -> np.ndarray:
        """Synchronous frame cropping for thread executor"""
        h, w = frame.shape[:2]
        target_width, target_height = target_size
        target_aspect = target_width / target_height
        
        # Determine crop center
        if crop_center:
            crop_center_x, crop_center_y = crop_center
        elif speaker_box:
            x, y, x1, y1 = speaker_box
            face_center_x = (x + x1) // 2
            face_center_y = (y + y1) // 2
            face_height = y1 - y
            padding_y = int(face_height * padding_factor) // 2
            crop_center_x = face_center_x
            crop_center_y = max(face_center_y - padding_y, face_center_y)
        else:
            # 🔧 FALLBACK: Use right side instead of center when no speaker or crop center specified
            crop_center_x = int(w * 0.75)  # 75% to the right
            crop_center_y = h // 2
        
        # Calculate crop dimensions
        if w / h > target_aspect:
            crop_height = h
            crop_width = int(h * target_aspect)
        else:
            crop_width = w
            crop_height = int(w / target_aspect)
        
        # Calculate crop boundaries
        left = max(0, crop_center_x - crop_width // 2)
        right = min(w, left + crop_width)
        top = max(0, crop_center_y - crop_height // 2)
        bottom = min(h, top + crop_height)
        
        # Adjust if needed
        if right - left < crop_width:
            if left == 0:
                right = min(w, crop_width)
            else:
                left = max(0, w - crop_width)
        
        if bottom - top < crop_height:
            if top == 0:
                bottom = min(h, crop_height)
            else:
                top = max(0, h - crop_height)
        
        # Perform crop
        cropped = frame[top:bottom, left:right]
        
        # Resize to target
        if cropped.shape[:2] != (target_height, target_width):
            cropped = cv2.resize(cropped, target_size)
        
        return cropped
    
    async def crop_frame_to_vertical(
        self, 
        frame: np.ndarray, 
        speaker_box: Optional[Tuple[int, int, int, int]],
        target_size: Tuple[int, int],
        crop_center: Optional[Tuple[int, int]] = None,
        padding_factor: float = 1.5
    ) -> np.ndarray:
        """Async frame cropping"""
        return await self._run_cpu_bound_task(
            self._crop_frame_to_vertical,
            frame, speaker_box, target_size, crop_center, padding_factor
        )
    
    def _extract_audio_sync(self, video_path: Path) -> Optional[bytes]:
        """Synchronous audio extraction"""
        try:
            temp_audio_path = f"temp_audio_vad_{uuid.uuid4().hex[:8]}.wav"
            audio = AudioSegment.from_file(str(video_path))
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(temp_audio_path, format="wav")
            
            with wave.open(temp_audio_path, 'rb') as wf:
                audio_data = wf.readframes(wf.getnframes())
            
            os.remove(temp_audio_path)
            return audio_data
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            return None
    
    async def extract_audio_for_vad(self, video_path: Path) -> Optional[bytes]:
        """Async audio extraction"""
        return await self._run_cpu_bound_task(self._extract_audio_sync, video_path)
    
    async def _detect_and_convert_av1_if_needed(self, video_path: Path) -> Path:
        """
        Detect AV1 codec and check if conversion is needed
        With conda-forge OpenCV, AV1 should work natively
        
        Returns:
            Path to usable video file (original or converted)
        """
        try:
            # First, try to detect the codec
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_streams', '-select_streams', 'v:0',
                '-print_format', 'json', str(video_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            codec_name = "unknown"
            if process.returncode == 0:
                try:
                    data = json.loads(stdout.decode())
                    streams = data.get('streams', [])
                    if streams:
                        codec_name = streams[0].get('codec_name', '').lower()
                        logger.info(f"🎬 Detected video codec: {codec_name}")
                        
                        # Check if it's AV1
                        if codec_name == 'av1':
                            logger.info(f"🎬 AV1 codec detected - testing conda-forge OpenCV compatibility...")
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Could not parse codec information")
            
            # Test if OpenCV can actually read frames from this video
            logger.info(f"🔍 Testing OpenCV compatibility with {codec_name} codec...")
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                if codec_name == 'av1':
                    logger.error(f"❌ conda-forge OpenCV cannot open AV1 video file - this is unexpected!")
                else:
                    logger.error(f"❌ OpenCV cannot open {codec_name} video file")
                cap.release()
                return await self._convert_to_h264(video_path)
            
            # Try to read first few frames to check for decoding issues
            frames_tested = 0
            successful_reads = 0
            
            for _ in range(10):  # Test first 10 frames
                ret, frame = cap.read()
                frames_tested += 1
                
                if ret and frame is not None:
                    successful_reads += 1
                elif not ret:
                    break  # End of video or critical error
            
            cap.release()
            
            # If we couldn't read any frames or success rate is too low, convert
            success_rate = successful_reads / frames_tested if frames_tested > 0 else 0
            
            if successful_reads == 0:
                if codec_name == 'av1':
                    logger.error(f"❌ conda-forge OpenCV cannot decode AV1 frames - fallback to H.264 conversion")
                else:
                    logger.error(f"❌ OpenCV cannot read any {codec_name} frames - converting to H.264")
                return await self._convert_to_h264(video_path)
            elif success_rate < 0.5:
                if codec_name == 'av1':
                    logger.warning(f"⚠️ conda-forge OpenCV AV1 decode success rate too low ({success_rate:.1%}) - converting to H.264")
                else:
                    logger.warning(f"⚠️ Low {codec_name} frame read success rate ({success_rate:.1%}) - converting to H.264")
                return await self._convert_to_h264(video_path)
            else:
                if codec_name == 'av1':
                    logger.info(f"✅ conda-forge OpenCV handling AV1 natively! ({success_rate:.1%} success rate)")
                else:
                    logger.info(f"✅ OpenCV can read {codec_name} video properly ({success_rate:.1%} success rate)")
                return video_path
                
        except Exception as e:
            logger.error(f"❌ Error testing video compatibility: {e}")
            # If testing fails, try converting as fallback, but don't fail completely if FFmpeg is missing
            try:
                return await self._convert_to_h264(video_path)
            except Exception as convert_error:
                logger.warning(f"⚠️ Conversion also failed: {convert_error}")
                logger.warning(f"⚠️ Proceeding with original video - results may be unreliable")
                return video_path
    
    async def _convert_to_h264(self, input_path: Path) -> Path:
        """
        Convert video to H.264 for better OpenCV compatibility
        
        Returns:
            Path to converted video file
        """
        try:
            # Create temporary file for converted video
            temp_dir = input_path.parent
            temp_filename = f"h264_converted_{uuid.uuid4().hex[:8]}_{input_path.name}"
            temp_path = temp_dir / temp_filename
            
            logger.info(f"🔄 Converting AV1/problematic video to H.264...")
            logger.info(f"   📁 Input: {input_path.name}")
            logger.info(f"   📁 Output: {temp_path.name}")
            
            # Use FFmpeg to convert to H.264 with good quality/speed balance
            cmd = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-i', str(input_path),
                '-c:v', 'libx264',
                '-preset', 'fast',  # Good balance of speed/quality
                # TODO: For faster AV1 conversion, could use 'ultrafast' preset and CRF 28
                # '-preset', 'ultrafast',  # Fastest encoding
                # '-crf', '28',           # Slightly lower quality for speed
                '-crf', '23',       # Good quality
                '-c:a', 'copy',     # Copy audio without re-encoding
                '-movflags', '+faststart',
                '-avoid_negative_ts', 'make_zero',
                '-threads', '0',    # Use all available CPU cores
                str(temp_path),
                '-y'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and temp_path.exists():
                file_size = temp_path.stat().st_size / (1024 * 1024)  # MB
                logger.info(f"✅ H.264 conversion successful ({file_size:.1f} MB)")
                return temp_path
            else:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                logger.error(f"❌ H.264 conversion failed: {error_msg}")
                
                # Clean up failed temp file
                if temp_path.exists():
                    temp_path.unlink()
                    
                # Return original file as last resort
                return input_path
                
        except Exception as e:
            logger.error(f"❌ Exception during H.264 conversion: {e}")
            return input_path
    
    def _process_audio_frames(self, audio_data: bytes, sample_rate: int = 16000, frame_duration_ms: int = 30):
        """Generator for audio frame processing"""
        if not audio_data:
            return
        
        n = int(sample_rate * frame_duration_ms / 1000) * 2
        offset = 0
        while offset + n <= len(audio_data):
            frame = audio_data[offset:offset + n]
            offset += n
            yield frame
    
    async def create_vertical_crop_async(
        self, 
        input_video_path: Path, 
        output_video_path: Path,
        use_speaker_detection: bool = True,
        use_smart_scene_detection: bool = True,
        enable_group_conversation_framing: bool = False,
        scene_content_threshold: float = 30.0,
        scene_fade_threshold: float = 8.0,
        scene_min_length: int = 15,
        ignore_micro_cuts: bool = True,
        micro_cut_threshold: int = 10,
        smoothing_strength: str = "very_high",
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create vertical crop asynchronously with smart scene detection and progress tracking
        
        Args:
            input_video_path: Path to input video
            output_video_path: Path to save cropped video
            use_speaker_detection: Whether to use speaker detection for smart cropping
            use_smart_scene_detection: Whether to use smart scene detection for crop resets
            enable_group_conversation_framing: Enable split-screen layout for 2-speaker conversations
            scene_content_threshold: Sensitivity for hard cuts (higher = less sensitive)
            scene_fade_threshold: Sensitivity for gradual transitions/fades
            scene_min_length: Minimum scene length in frames to avoid micro-cuts
            ignore_micro_cuts: Whether to ignore very short scenes
            micro_cut_threshold: Threshold for micro-cut detection in frames
            smoothing_strength: Motion smoothing level
            task_id: Optional task ID for tracking
        """
        if not task_id:
            task_id = self._create_task_id()
        
        # Check concurrent task limit
        with self.task_lock:
            active_count = len([t for t in self.active_tasks.values() if t["status"] == "processing"])
            if active_count >= self.max_concurrent_tasks:
                return {
                    "success": False,
                    "error": f"Maximum concurrent tasks ({self.max_concurrent_tasks}) reached",
                    "task_id": task_id
                }
        
        # Initialize task tracking
        with self.task_lock:
            self.active_tasks[task_id] = {
                "task_id": task_id,
                "status": "initializing",
                "progress": 0,
                "message": "Initializing video processing...",
                "created_at": datetime.now(),
                "input_path": str(input_video_path),
                "output_path": str(output_video_path),
                "use_speaker_detection": use_speaker_detection,
                "use_smart_scene_detection": use_smart_scene_detection,
                "enable_group_conversation_framing": enable_group_conversation_framing,
                "smoothing_strength": smoothing_strength
            }
        
        # Initialize variables for cleanup tracking
        actual_video_path = input_video_path
        is_converted = False
        
        try:
            # 🔧 AV1 COMPATIBILITY FIX - Check and convert if needed
            self._update_task_status(task_id, "processing", 2, "Checking video codec compatibility...")
            
            actual_video_path = await self._detect_and_convert_av1_if_needed(input_video_path)
            is_converted = actual_video_path != input_video_path
            
            if is_converted:
                logger.info(f"🔄 Using converted H.264 video for processing")
                self._update_task_status(task_id, "processing", 5, "Using H.264 converted video...")
            else:
                self._update_task_status(task_id, "processing", 5, "Reading video properties...")
            
            # Get video properties from the (possibly converted) video
            cap = cv2.VideoCapture(str(actual_video_path))
            if not cap.isOpened():
                # If even the converted video fails, this is a more serious issue
                error_msg = f"Could not open video even after conversion attempt: {actual_video_path}"
                if is_converted and actual_video_path.exists():
                    actual_video_path.unlink()  # Clean up converted file
                raise Exception(error_msg)
            
            original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            # Calculate target size
            target_height = original_height
            target_width = int(original_height * (9 / 16))
            if target_width % 2 != 0:
                target_width += 1
            target_size = (target_width, target_height)
            
            # Configure smoothing
            smoothing_configs = {
                "low": {"smoothing_factor": 0.3, "max_jump_distance": 80, "stability_frames": 3},
                "medium": {"smoothing_factor": 0.75, "max_jump_distance": 50, "stability_frames": 5},
                "high": {"smoothing_factor": 0.9, "max_jump_distance": 25, "stability_frames": 8},
                "very_high": {"smoothing_factor": 0.95, "max_jump_distance": 15, "stability_frames": 12}  # 🔧 Reduced jump distance to prevent twitches
            }
            
            smoothing_config = smoothing_configs.get(smoothing_strength, smoothing_configs["medium"])
            
            self._update_task_status(
                task_id, "processing", 10, 
                f"Video: {target_size[0]}x{target_size[1]}, {fps}fps, {total_frames} frames"
            )
            
            # 🎬 SMART SCENE DETECTION - Pre-compute all scene boundaries upfront
            scene_data = {"scene_boundaries": set(), "scene_stats": [], "scene_count": 0}
            if use_smart_scene_detection and SCENEDETECT_AVAILABLE:
                self._update_task_status(task_id, "processing", 12, "🎬 Smart scene analysis - scanning for cuts...")
                
                try:
                    scene_data = await self._smart_scene_detection(
                        input_video_path, 
                        scene_content_threshold, 
                        scene_fade_threshold, 
                        scene_min_length,
                        use_fade_detection=True
                    )
                    
                    cut_count = len(scene_data.get("scene_boundaries", set()))
                    scene_count = scene_data.get("scene_count", 0)
                    
                    if cut_count > 0:
                        logger.info(f"🎬 Smart scene detection found {scene_count} scenes with {cut_count} cut boundaries")
                        self._update_task_status(
                            task_id, "processing", 15, 
                            f"🎬 Found {scene_count} scenes, {cut_count} cuts - ready for smart cropping"
                        )
                    else:
                        logger.info(f"🎬 No scene changes detected - using continuous smoothing")
                        self._update_task_status(task_id, "processing", 15, "🎬 No scene changes detected - continuous smoothing")
                        
                except Exception as e:
                    logger.error(f"🎬 Scene detection failed completely: {e}")
                    logger.info(f"🎬 Continuing with standard cropping (no scene detection)")
                    scene_data = {"scene_boundaries": set(), "scene_stats": [], "scene_count": 0}
                    self._update_task_status(task_id, "processing", 15, "🎬 Scene detection failed - using standard cropping")
            else:
                logger.info(f"🎬 Scene detection disabled - using standard cropping")
                self._update_task_status(task_id, "processing", 15, "Smart scene detection disabled")
            
            # Ensure scene_data always has the required keys
            scene_data.setdefault("scene_boundaries", set())
            scene_data.setdefault("scene_stats", [])
            scene_data.setdefault("scene_count", 0)
            scene_data.setdefault("cut_boundaries", [])
            
            logger.info(f"🎬 Proceeding to video processing with {scene_data['scene_count']} detected scenes")
            
            # Extract audio if needed
            audio_data = None
            if use_speaker_detection and self.vad:
                self._update_task_status(task_id, "processing", 17, "Extracting audio for voice detection...")
                audio_data = await self.extract_audio_for_vad(actual_video_path)
            
            # Process video with smart scene awareness
            self._update_task_status(task_id, "processing", 20, "Starting smart video processing...")
            
            # ALWAYS continue to video processing regardless of scene detection result
            logger.info(f"🎬 Starting video frame processing...")
            result = await self._process_video_frames_smart(
                task_id, actual_video_path, output_video_path, 
                target_size, smoothing_config, audio_data,
                use_speaker_detection, enable_group_conversation_framing, fps, total_frames, scene_data,
                ignore_micro_cuts, micro_cut_threshold
            )
            
            if result["success"]:
                scene_info = ""
                if scene_data["scene_count"] > 0:
                    scene_info = f", {scene_data['scene_count']} scenes, {result.get('smart_resets', 0)} smart resets"
                
                self._update_task_status(
                    task_id, "completed", 100, 
                    f"Smart video processing completed! Output: {output_video_path}{scene_info}",
                    {
                        "output_path": str(output_video_path), 
                        "file_size_mb": result.get("file_size_mb", 0),
                        "scenes_detected": scene_data["scene_count"],
                        "smart_resets": result.get("smart_resets", 0),
                        "cut_boundaries": scene_data.get("cut_boundaries", [])
                    }
                )
            else:
                self._update_task_status(
                    task_id, "failed", 0, 
                    f"Processing failed: {result.get('error', 'Unknown error')}"
                )
            
            # 🧹 Cleanup converted H.264 file if we created one
            if is_converted and actual_video_path.exists():
                try:
                    actual_video_path.unlink()
                    logger.info(f"🧹 Cleaned up temporary H.264 file: {actual_video_path.name}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Could not clean up temporary file {actual_video_path.name}: {cleanup_error}")
            
            return {
                "success": result["success"],
                "task_id": task_id,
                "output_path": str(output_video_path) if result["success"] else None,
                "scenes_detected": scene_data["scene_count"],
                "smart_resets": result.get("smart_resets", 0),
                "error": result.get("error")
            }
            
        except Exception as e:
            logger.error(f"❌ Smart vertical crop failed for task {task_id}: {str(e)}")
            
            # 🧹 Cleanup converted H.264 file if we created one (even on error)
            if is_converted and actual_video_path.exists():
                try:
                    actual_video_path.unlink()
                    logger.info(f"🧹 Cleaned up temporary H.264 file after error: {actual_video_path.name}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Could not clean up temporary file {actual_video_path.name}: {cleanup_error}")
            
            self._update_task_status(task_id, "failed", 0, f"Error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }
    
    async def _process_video_frames_smart(
        self,
        task_id: str,
        input_video_path: Path,
        output_video_path: Path,
        target_size: Tuple[int, int],
        smoothing_config: Dict[str, Any],
        audio_data: Optional[bytes],
        use_speaker_detection: bool,
        enable_group_conversation_framing: bool,
        fps: int,
        total_frames: int,
        scene_data: Dict[str, Any],
        ignore_micro_cuts: bool,
        micro_cut_threshold: int
    ) -> Dict[str, Any]:
        """Process video frames with smart scene-aware cropping and explicit reset events"""
        try:
            logger.info(f"🎬 Starting smart video frame processing...")
            logger.info(f"   📁 Input: {input_video_path}")
            logger.info(f"   📁 Output: {output_video_path}")
            logger.info(f"   📊 Resolution: {target_size}")
            logger.info(f"   🎬 Scene boundaries: {len(scene_data.get('scene_boundaries', set()))}")
            logger.info(f"   🎛️ Total frames to process: {total_frames}")

            # Setup temp video path
            temp_video_path = output_video_path.with_name(f"{output_video_path.stem}_temp_{task_id}.mp4")
            temp_video_path.parent.mkdir(parents=True, exist_ok=True)

            # Extract scene information
            scene_boundaries = scene_data.get("scene_boundaries", set())
            scene_stats = scene_data.get("scene_stats", [])

            previous_crop_center = None
            recent_centers = []
            smart_resets = 0
            last_dual_speaker_frame = -999
            dual_speaker_stability_threshold = fps // 6

            logger.info(f"🎬 Starting smart processing with {len(scene_boundaries)} scene boundaries")

            # Setup audio generator
            audio_generator = None
            if audio_data:
                logger.info(f"🔊 Audio data available for voice detection")
                audio_generator = self._process_audio_frames(audio_data)
            else:
                logger.info(f"🔇 No audio data - using visual detection only")

            # Use OpenCV directly since conda-forge handles AV1 perfectly
            import cv2
            import numpy as np
            frame_count = 0
            last_progress_update = 0

            # Setup video writer for temp output
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(temp_video_path), fourcc, fps, target_size)
            if not out.isOpened():
                raise Exception(f"Could not open video writer for: {temp_video_path} - no compatible codec found")

            # Use OpenCV VideoCapture directly (works great with conda-forge AV1 support)
            cap = cv2.VideoCapture(str(input_video_path))
            if not cap.isOpened():
                raise Exception(f"Could not open video with OpenCV: {input_video_path}")
            
            logger.info(f"🎬 Using OpenCV VideoCapture for frame processing (AV1 native support)")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                # SMART SCENE RESET LOGIC
                should_reset = self._apply_smart_reset(
                    frame_count, scene_boundaries, scene_stats, 
                    ignore_micro_cuts, micro_cut_threshold
                )
                if should_reset:
                    smart_resets += 1
                    recent_centers.clear()
                    previous_crop_center = None
                    logger.info(f"🎬 Smart reset #{smart_resets} at frame {frame_count} - fresh start")
                    if frame_count - last_progress_update >= (fps * 2):
                        progress = 20 + int((frame_count / total_frames) * 60)
                        self._update_task_status(
                            task_id, "processing", progress,
                            f"🎬 Smart reset #{smart_resets} at frame {frame_count} - refocusing"
                        )
                        last_progress_update = frame_count
                # Get audio frame
                audio_frame = None
                if audio_generator:
                    try:
                        audio_frame = next(audio_generator)
                    except StopIteration:
                        audio_frame = None
                # SMART SPEAKER DETECTION
                speaker_result = None
                if use_speaker_detection:
                    speaker_result = await self.find_active_speaker(
                        frame, audio_frame, previous_crop_center, enable_group_conversation_framing
                    )
                can_use_dual_speaker = (
                    speaker_result and 
                    isinstance(speaker_result, dict) and 
                    speaker_result.get("mode") == "dual_speaker" and
                    (frame_count - last_dual_speaker_frame) >= dual_speaker_stability_threshold
                )
                if can_use_dual_speaker:
                    last_dual_speaker_frame = frame_count
                    cropped_frame = await self.create_dual_speaker_frame(
                        frame, 
                        speaker_result["speaker_1"], 
                        speaker_result["speaker_2"], 
                        target_size
                    )
                    h, w = frame.shape[:2]
                    if previous_crop_center is None:
                        previous_crop_center = (int(w * 0.75), h // 2)
                        recent_centers = [(int(w * 0.75), h // 2)]
                else:
                    speaker_box = speaker_result if isinstance(speaker_result, tuple) else None
                    if speaker_box:
                        x, y, x1, y1 = speaker_box
                        raw_center = ((x + x1) // 2, (y + y1) // 2)
                    else:
                        h, w = frame.shape[:2]
                        raw_center = (int(w * 0.75), h // 2)
                    if should_reset:
                        crop_center = raw_center
                        recent_centers = [raw_center]
                    else:
                        crop_center, recent_centers = self._smooth_crop_center(
                            raw_center, previous_crop_center, recent_centers, smoothing_config
                        )
                    previous_crop_center = crop_center
                    cropped_frame = await self.crop_frame_to_vertical(
                        frame, speaker_box, target_size, crop_center
                    )
                out.write(cropped_frame)
                frame_count += 1
                if frame_count % (fps * 5) == 0:
                    logger.info(f"📊 Processed {frame_count} frames...")
            
            # Clean up video capture and writer
            cap.release()
            out.release()
            logger.info(f"🎬 Frame processing complete. Proceeding to audio merging...")
            # --- AUDIO INTEGRATION STEP (unchanged) ---
            try:
                from moviepy import VideoFileClip
                if not temp_video_path.exists():
                    logger.error(f"Temp video not found: {temp_video_path}")
                    return {"success": False, "error": "Temp video not found"}
                with VideoFileClip(str(input_video_path)) as original_clip:
                    if original_clip.audio is None:
                        logger.warning("⚠️ Original video has no audio. The output will be silent.")
                        temp_video_path.rename(output_video_path)
                        return {"success": True, "output_path": str(output_video_path)}
                cmd = [
                    'ffmpeg',
                    '-hide_banner', '-loglevel', 'error',
                    '-i', str(temp_video_path),
                    '-i', str(input_video_path),
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-shortest',
                    str(output_video_path),
                    '-y'
                ]
                import subprocess
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    logger.info(f"✅ Audio successfully merged! Final video: {output_video_path}")
                    if temp_video_path.exists():
                        os.remove(temp_video_path)
                    return {"success": True, "output_path": str(output_video_path)}
                else:
                    logger.error(f"❌ Failed to merge audio with ffmpeg: {result.stderr.strip()}")
                    if temp_video_path.exists():
                        temp_video_path.rename(output_video_path)
                        logger.warning(f"⚠️ Fallback: Saved SILENT video to {output_video_path}")
                    return {"success": False, "error": "Failed to merge audio"}
            except Exception as e:
                logger.error(f"❌ An unexpected error occurred during audio merging: {e}")
                if temp_video_path.exists():
                    temp_video_path.rename(output_video_path)
                    logger.warning(f"⚠️ Fallback: Saved SILENT video to {output_video_path}")
                return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"❌ Smart frame processing failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _add_audio_to_video(self, temp_video_path: Path, input_video_path: Path, output_video_path: Path) -> bool:
        """Add audio back to processed video with enhanced sync preservation"""
        try:
            from .audio_sync_manager import get_audio_sync_manager
            
            # Use the enhanced audio sync manager
            sync_manager = await get_audio_sync_manager()
            
            logger.info("🔊 Using enhanced audio sync manager for audio merge...")
            
            # Apply the vertical crop audio fix
            success = await sync_manager.fix_vertical_crop_audio(
                temp_video_path, input_video_path, output_video_path, preserve_timing=True
            )
            
            if success:
                # Clean up temp file
                if temp_video_path.exists():
                    os.remove(temp_video_path)
                return True
            else:
                logger.warning("Enhanced audio sync failed, trying fallback...")
                return await self._fallback_audio_merge(temp_video_path, input_video_path, output_video_path)
                
        except Exception as e:
            logger.error(f"Enhanced audio merge error: {e}")
            return await self._fallback_audio_merge(temp_video_path, input_video_path, output_video_path)
    
    async def _fallback_audio_merge(self, temp_video_path: Path, input_video_path: Path, output_video_path: Path) -> bool:
        """Fallback audio merge with basic sync preservation"""
        try:
            # Check if original has audio
            with VideoFileClip(str(input_video_path)) as original_clip:
                if original_clip.audio is None:
                    temp_video_path.rename(output_video_path)
                    return True
            
            # Enhanced ffmpeg command with better sync preservation
            cmd = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-i', str(temp_video_path),
                '-i', str(input_video_path),
                '-c:v', 'copy', 
                '-c:a', 'aac',  # Re-encode audio for better compatibility
                '-b:a', '192k',  # High audio bitrate
                '-ar', '48000',  # Standard sample rate
                '-map', '0:v:0', '-map', '1:a:0',
                '-fflags', '+genpts',  # Generate presentation timestamps
                '-avoid_negative_ts', 'make_zero',
                '-movflags', '+faststart',
                str(output_video_path), '-y'
            ]
            
            # Run ffmpeg asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Clean up temp file
                if temp_video_path.exists():
                    os.remove(temp_video_path)
                return True
            else:
                logger.error(f"Fallback audio merge failed: {stderr.decode()}")
                # Last resort: rename temp file
                if temp_video_path.exists():
                    temp_video_path.rename(output_video_path)
                return False
                
        except Exception as e:
            logger.error(f"Fallback audio merge error: {e}")
            if temp_video_path.exists():
                temp_video_path.rename(output_video_path)
            return False
    
    async def _smart_scene_detection(
        self, 
        video_path: Path, 
        content_threshold: float = 30.0,
        fade_threshold: float = 8.0,
        min_scene_len: int = 15,
        use_fade_detection: bool = True
    ) -> Dict[str, Any]:
        """
        Smart scene detection with timeout protection and robust fallback
        
        Args:
            video_path: Path to video file
            content_threshold: Sensitivity for hard cuts (higher = less sensitive)
            fade_threshold: Sensitivity for gradual transitions/fades
            min_scene_len: Minimum scene length in frames to avoid micro-cuts
            use_fade_detection: Whether to detect gradual fades as scene changes
            
        Returns:
            Dict with scene_boundaries (set), scene_stats, and metadata
        """
        if not SCENEDETECT_AVAILABLE:
            logger.warning("⚠️ PySceneDetect not available. Smart scene detection skipped.")
            return {"scene_boundaries": set(), "scene_count": 0, "scene_stats": [], "total_duration": 0, "cut_boundaries": []}
        
        try:
            logger.info(f"🎬 Starting async scene detection with 60s timeout...")
            
            # Run scene detection in thread executor with timeout
            result = await asyncio.wait_for(
                self._run_cpu_bound_task(
                    self._detect_scenes_smart_sync, 
                    video_path, content_threshold, fade_threshold, min_scene_len, use_fade_detection
                ),
                timeout=60.0  # 60 second timeout
            )
            
            if result and result.get("scene_count", 0) > 0:
                logger.info(f"🎬 Scene detection successful: {result['scene_count']} scenes found")
            else:
                logger.info(f"🎬 Scene detection completed but no scenes found - using fallback")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"🎬 Scene detection timeout (60s) - continuing without scene detection")
            return {"scene_boundaries": set(), "scene_count": 0, "scene_stats": [], "total_duration": 0, "cut_boundaries": []}
        except Exception as e:
            logger.error(f"🎬 Async scene detection failed: {e}")
            logger.error(f"🎬 Continuing without scene detection to ensure cropping happens")
            return {"scene_boundaries": set(), "scene_count": 0, "scene_stats": [], "total_duration": 0, "cut_boundaries": []}
    
    def _detect_scenes_smart_sync(
        self, 
        video_path: Path, 
        content_threshold: float = 30.0,
        fade_threshold: float = 8.0,
        min_scene_len: int = 15,
        use_fade_detection: bool = True
    ) -> Dict[str, Any]:
        """Synchronous smart scene detection with multiple detectors and robust error handling"""
        try:
            logger.info(f"🎬 Starting scene detection for: {video_path}")
            
            # Create video manager and scene manager
            video_manager = VideoManager([str(video_path)])
            scene_manager = SceneManager()
            
            # Add multiple detectors for comprehensive scene detection
            scene_manager.add_detector(ContentDetector(threshold=content_threshold, min_scene_len=min_scene_len))
            
            if use_fade_detection:
                scene_manager.add_detector(ThresholdDetector(threshold=fade_threshold, min_scene_len=min_scene_len))
            
            # Set duration and start with timeout protection
            video_manager.set_duration()
            video_manager.start()
            
            logger.info(f"🎬 Video manager started, detecting scenes...")
            
            # Perform scene detection with progress feedback
            scene_manager.detect_scenes(frame_source=video_manager)
            
            logger.info(f"🎬 Scene detection completed, processing results...")
            
            # Get scene list and convert to frame numbers for easy lookup
            scene_list = scene_manager.get_scene_list()
            scene_boundaries = set()
            scene_stats = []
            
            if not scene_list:
                logger.warning("�� No scenes detected - video might be very stable or detection failed")
                video_manager.release()
                return {
                    "scene_boundaries": set(),
                    "scene_count": 0,
                    "scene_stats": [],
                    "total_duration": 0,
                    "cut_boundaries": []
                }
            
            for i, (start_time, end_time) in enumerate(scene_list):
                start_frame = int(start_time.get_frames())
                end_frame = int(end_time.get_frames())
                scene_length = end_frame - start_frame
                
                # Add end frame as boundary (where next scene starts)
                if i < len(scene_list) - 1:  # Don't add boundary after last scene
                    scene_boundaries.add(end_frame)
                
                scene_stats.append({
                    "scene_id": i,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "length_frames": scene_length,
                    "start_time": start_time.get_seconds(),
                    "end_time": end_time.get_seconds(),
                    "duration": end_time.get_seconds() - start_time.get_seconds()
                })
            
            video_manager.release()
            
            total_duration = scene_list[-1][1].get_seconds() if scene_list else 0
            
            logger.info(f"🎬 Smart scene detection complete:")
            logger.info(f"   └─ {len(scene_list)} scenes detected")
            logger.info(f"   └─ {len(scene_boundaries)} cut boundaries found")
            logger.info(f"   └─ Scene boundaries at frames: {sorted(list(scene_boundaries))}")
            
            return {
                "scene_boundaries": scene_boundaries,
                "scene_count": len(scene_list),
                "scene_stats": scene_stats,
                "total_duration": total_duration,
                "cut_boundaries": sorted(list(scene_boundaries))
            }
            
        except Exception as e:
            logger.error(f"🎬 Scene detection sync error: {e}")
            logger.error(f"🎬 Falling back to no scene detection")
            # Always return valid empty result to allow processing to continue
            return {
                "scene_boundaries": set(),
                "scene_count": 0,
                "scene_stats": [],
                "total_duration": 0,
                "cut_boundaries": []
            }
    
    def _should_ignore_micro_cut(self, frame_idx: int, scene_stats: List[Dict], micro_cut_threshold: int = 10) -> bool:
        """
        Check if this is a micro-cut that should be ignored
        
        Args:
            frame_idx: Current frame index
            scene_stats: List of scene statistics
            micro_cut_threshold: Ignore scenes shorter than this many frames
            
        Returns:
            True if this is a micro-cut to ignore
        """
        for scene in scene_stats:
            if scene["start_frame"] <= frame_idx < scene["end_frame"]:
                return scene["length_frames"] < micro_cut_threshold
        return False
    
    def _apply_smart_reset(
        self, 
        frame_idx: int, 
        scene_boundaries: set, 
        scene_stats: List[Dict],
        ignore_micro_cuts: bool = True,
        micro_cut_threshold: int = 10
    ) -> bool:
        """
        Determine if we should apply a smart reset at this frame
        
        Args:
            frame_idx: Current frame index
            scene_boundaries: Set of frame indices where scenes change
            scene_stats: Scene statistics for micro-cut detection
            ignore_micro_cuts: Whether to ignore very short scenes
            micro_cut_threshold: Threshold for micro-cut detection
            
        Returns:
            True if we should reset crop smoothing
        """
        if frame_idx not in scene_boundaries:
            return False
        
        if ignore_micro_cuts and self._should_ignore_micro_cut(frame_idx, scene_stats, micro_cut_threshold):
            logger.debug(f"🎬 Ignoring micro-cut at frame {frame_idx}")
            return False
        
        return True
    
    def _create_dual_speaker_frame_sync(
        self,
        frame: np.ndarray,
        speaker_1_box: Tuple[int, int, int, int],
        speaker_2_box: Tuple[int, int, int, int],
        target_size: Tuple[int, int],
        padding_factor: float = 1.3
    ) -> np.ndarray:
        """
        Create a split-screen vertical frame with two speakers
        Top half: Speaker 1, Bottom half: Speaker 2
        """
        target_width, target_height = target_size
        half_height = target_height // 2
        
        # Create individual crops for each speaker
        speaker_1_crop = self._crop_single_speaker_region(
            frame, speaker_1_box, (target_width, half_height), padding_factor
        )
        
        speaker_2_crop = self._crop_single_speaker_region(
            frame, speaker_2_box, (target_width, half_height), padding_factor
        )
        
        # Combine into split-screen layout
        dual_frame = np.zeros((target_height, target_width, 3), dtype=np.uint8)
        dual_frame[0:half_height, :] = speaker_1_crop  # Top half
        dual_frame[half_height:target_height, :] = speaker_2_crop  # Bottom half
        
        # Optional: Add a subtle divider line
        divider_y = half_height
        cv2.line(dual_frame, (0, divider_y), (target_width, divider_y), (40, 40, 40), 2)
        
        return dual_frame
    
    def _crop_single_speaker_region(
        self,
        frame: np.ndarray,
        speaker_box: Tuple[int, int, int, int],
        target_size: Tuple[int, int],
        padding_factor: float = 1.3
    ) -> np.ndarray:
        """
        Crop a single speaker region with smart framing
        """
        h, w = frame.shape[:2]
        target_width, target_height = target_size
        
        x, y, x1, y1 = speaker_box
        face_center_x = (x + x1) // 2
        face_center_y = (y + y1) // 2
        face_height = y1 - y
        
        # Add padding above the face for better framing
        padding_y = int(face_height * padding_factor) // 2
        crop_center_x = face_center_x
        crop_center_y = max(face_center_y - padding_y, face_center_y)
        
        # Calculate crop dimensions maintaining aspect ratio
        target_aspect = target_width / target_height
        
        if w / h > target_aspect:
            crop_height = min(h, int(target_height * 0.8))  # Use 80% of available height for better framing
            crop_width = int(crop_height * target_aspect)
        else:
            crop_width = min(w, int(target_width * 0.8))
            crop_height = int(crop_width / target_aspect)
        
        # Calculate crop boundaries
        left = max(0, crop_center_x - crop_width // 2)
        right = min(w, left + crop_width)
        top = max(0, crop_center_y - crop_height // 2)
        bottom = min(h, top + crop_height)
        
        # Adjust if boundaries are out of frame
        if right - left < crop_width:
            if left == 0:
                right = min(w, crop_width)
            else:
                left = max(0, w - crop_width)
        
        if bottom - top < crop_height:
            if top == 0:
                bottom = min(h, crop_height)
            else:
                top = max(0, h - crop_height)
        
        # Perform crop
        cropped = frame[top:bottom, left:right]
        
        # Resize to exact target size
        if cropped.shape[:2] != (target_height, target_width):
            cropped = cv2.resize(cropped, target_size)
        
        return cropped
    
    async def create_dual_speaker_frame(
        self,
        frame: np.ndarray,
        speaker_1_box: Tuple[int, int, int, int],
        speaker_2_box: Tuple[int, int, int, int],
        target_size: Tuple[int, int],
        padding_factor: float = 1.3
    ) -> np.ndarray:
        """Async dual-speaker frame creation"""
        return await self._run_cpu_bound_task(
            self._create_dual_speaker_frame_sync,
            frame, speaker_1_box, speaker_2_box, target_size, padding_factor
        )

# Global async service instance
async_vertical_crop_service = AsyncVerticalCropService()

# Convenience functions
async def crop_video_to_vertical_async(
    input_path: Path,
    output_path: Path,
    use_speaker_detection: bool = True,
    use_smart_scene_detection: bool = True,
    enable_group_conversation_framing: bool = False,
    scene_content_threshold: float = 30.0,
    scene_fade_threshold: float = 8.0,
    scene_min_length: int = 15,
    ignore_micro_cuts: bool = True,
    micro_cut_threshold: int = 10,
    smoothing_strength: str = "very_high",
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Async convenience function to crop video to vertical format with smart scene detection
    
    This implements the intelligent scene-aware cropping system where PySceneDetect
    acts as the "brain" telling your smoothing when to reset for perfect responsiveness
    on every real cut while maintaining smooth tracking in stable scenes.
    
    Args:
        input_path: Path to input video
        output_path: Path to save cropped video
        use_speaker_detection: Whether to use speaker detection for smart cropping
        use_smart_scene_detection: Whether to use smart scene detection for crop resets
        enable_group_conversation_framing: Enable split-screen layout for 2-speaker conversations
        scene_content_threshold: Sensitivity for hard cuts (higher = less sensitive, 30.0 = default)
        scene_fade_threshold: Sensitivity for gradual transitions/fades (8.0 = default)
        scene_min_length: Minimum scene length in frames to avoid micro-cuts (15 = default)
        ignore_micro_cuts: Whether to ignore very short scenes (True = recommended)
        micro_cut_threshold: Threshold for micro-cut detection in frames (10 = default)
        smoothing_strength: Motion smoothing level ("very_high" = most stable)
        task_id: Optional task ID for tracking
    
    Returns:
        Dict with success, task_id, output_path, scenes_detected, smart_resets, error keys
    """
    return await async_vertical_crop_service.create_vertical_crop_async(
        input_path, output_path, use_speaker_detection, use_smart_scene_detection,
        enable_group_conversation_framing, scene_content_threshold, scene_fade_threshold, scene_min_length,
        ignore_micro_cuts, micro_cut_threshold, smoothing_strength, task_id
    )

async def get_crop_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a cropping task"""
    return await async_vertical_crop_service.get_task_status(task_id)

async def list_crop_tasks() -> Dict[str, Dict[str, Any]]:
    """List all active cropping tasks"""
    return await async_vertical_crop_service.list_active_tasks()

async def cleanup_old_crop_tasks(max_age_hours: int = 24):
    """Clean up old completed tasks"""
    await async_vertical_crop_service.cleanup_completed_tasks(max_age_hours) 