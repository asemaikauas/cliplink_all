"""
Vertical cropping service for creating YouTube Shorts (9:16 aspect ratio)
Based on AI-Youtube-Shorts-Generator methodology with speaker detection and smart cropping
"""

import cv2
import numpy as np
import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List
import webrtcvad
import wave
import contextlib
from pydub import AudioSegment
from moviepy import VideoFileClip, AudioFileClip
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VerticalCropService:
    """
    Service for creating vertical (9:16) crops of videos with intelligent speaker tracking
    """
    
    def __init__(self):
        # Initialize VAD for voice activity detection
        try:
            self.vad = webrtcvad.Vad(2)  # Aggressiveness mode 0-3
            logger.info("✅ Voice Activity Detection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize VAD: {e}")
            self.vad = None
        
        # Try to load OpenCV DNN model for face detection
        self.face_net = self._load_face_detection_model()
        
        # 🎯 ДОБАВЛЯЕМ СТАБИЛИЗАЦИЮ
        self.previous_crop_center = None
        self.smoothing_factor = 0.75  # Коэффициент сглаживания (0-1, чем больше - тем плавнее)
        self.max_jump_distance = 80   # Максимальное расстояние прыжка за кадр в пикселях
        self.stability_frames = 5     # Количество кадров для усреднения
        self.recent_centers = []      # История недавних центров
    
    def _load_face_detection_model(self):
        """Load OpenCV DNN model for face detection"""
        try:
            # You'll need to download these models
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
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in frame using OpenCV DNN
        Returns list of face bounding boxes (x, y, x1, y1)
        """
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
                if confidence > 0.5:  # Confidence threshold
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    x, y, x1, y1 = box.astype("int")
                    faces.append((x, y, x1, y1))
            
            return faces
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []
    
    def detect_voice_activity(self, audio_frame: bytes) -> bool:
        """Detect if there's voice activity in audio frame"""
        if self.vad is None:
            return True  # Assume activity if VAD not available
        
        try:
            return self.vad.is_speech(audio_frame, 16000)
        except Exception as e:
            logger.error(f"Voice activity detection error: {e}")
            return True
    
    def find_active_speaker(self, frame: np.ndarray, audio_frame: Optional[bytes] = None) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the most likely active speaker in the frame
        Returns bounding box (x, y, x1, y1) or None
        """
        faces = self.detect_faces(frame)
        
        if not faces:
            return None
        
        # If only one face, return it
        if len(faces) == 1:
            return faces[0]
        
        # Multiple faces: use heuristics to find active speaker
        h, w = frame.shape[:2]
        best_face = None
        best_score = 0
        
        # Check voice activity
        has_voice_activity = True
        if audio_frame:
            has_voice_activity = self.detect_voice_activity(audio_frame)
        
        for face in faces:
            x, y, x1, y1 = face
            face_width = x1 - x
            face_height = y1 - y
            
            # Score based on face size (larger faces are more likely to be speakers)
            size_score = (face_width * face_height) / (w * h)
            
            # Score based on position (center faces are more likely to be speakers)
            face_center_x = (x + x1) / 2
            face_center_y = (y + y1) / 2
            center_score = 1.0 - (abs(face_center_x - w/2) / (w/2))
            
            # 🎯 БОНУС ЗА СТАБИЛЬНОСТЬ: предпочитаем лица близко к предыдущей позиции
            stability_score = 0
            if self.previous_crop_center:
                prev_x, prev_y = self.previous_crop_center
                distance = np.sqrt((face_center_x - prev_x)**2 + (face_center_y - prev_y)**2)
                # Преобразуем расстояние в оценку (ближе = выше оценка)
                max_distance = np.sqrt(w**2 + h**2) / 3  # Треть диагонали
                stability_score = max(0, 1.0 - distance / max_distance)
            
            # Комбинируем оценки с весом стабильности
            total_score = (
                size_score * 0.35 + 
                center_score * 0.25 + 
                stability_score * 0.4  # Приоритет стабильности!
            )
            
            if has_voice_activity:
                total_score *= 1.15  # Небольшой буст за голосовую активность
            
            if total_score > best_score:
                best_score = total_score
                best_face = face
        
        return best_face

    def _smooth_crop_center(self, new_center: Tuple[int, int]) -> Tuple[int, int]:
        """
        🎯 СГЛАЖИВАНИЕ ЦЕНТРА КРОПА ДЛЯ УМЕНЬШЕНИЯ ДЁРГАНЬЯ
        Применяет многоуровневое сглаживание
        """
        if self.previous_crop_center is None:
            self.previous_crop_center = new_center
            self.recent_centers = [new_center]
            return new_center
        
        # Добавляем новый центр в историю
        self.recent_centers.append(new_center)
        if len(self.recent_centers) > self.stability_frames:
            self.recent_centers.pop(0)
        
        # Вычисляем среднее по последним кадрам
        avg_x = sum(center[0] for center in self.recent_centers) / len(self.recent_centers)
        avg_y = sum(center[1] for center in self.recent_centers) / len(self.recent_centers)
        averaged_center = (int(avg_x), int(avg_y))
        
        prev_x, prev_y = self.previous_crop_center
        new_x, new_y = averaged_center
        
        # Вычисляем расстояние движения
        distance = np.sqrt((new_x - prev_x)**2 + (new_y - prev_y)**2)
        
        # Ограничиваем слишком резкие движения
        if distance > self.max_jump_distance:
            # Вычисляем направление и ограничиваем расстояние
            direction_x = (new_x - prev_x) / distance if distance > 0 else 0
            direction_y = (new_y - prev_y) / distance if distance > 0 else 0
            
            new_x = prev_x + direction_x * self.max_jump_distance
            new_y = prev_y + direction_y * self.max_jump_distance
        
        # Применяем экспоненциальное сглаживание
        smoothed_x = int(prev_x * self.smoothing_factor + new_x * (1 - self.smoothing_factor))
        smoothed_y = int(prev_y * self.smoothing_factor + new_y * (1 - self.smoothing_factor))
        
        # Обновляем предыдущую позицию
        self.previous_crop_center = (smoothed_x, smoothed_y)
        
        return (smoothed_x, smoothed_y)
    
    def crop_to_vertical(
        self, 
        frame: np.ndarray, 
        speaker_box: Optional[Tuple[int, int, int, int]] = None,
        target_size: Tuple[int, int] = (608, 1080),
        padding_factor: float = 1.5,
        use_smoothing: bool = True
    ) -> np.ndarray:
        """
        Crop frame to vertical format (9:16) centered on speaker or frame center
        
        Args:
            frame: Input frame
            speaker_box: Bounding box of speaker (x, y, x1, y1)
            target_size: Target resolution (width, height)
            padding_factor: How much space around the speaker to include
            use_smoothing: Whether to apply smoothing to reduce jerkiness
        """
        h, w = frame.shape[:2]
        target_width, target_height = target_size
        
        # Calculate target aspect ratio
        target_aspect = target_width / target_height
        
        # Определяем начальный центр кропа
        if speaker_box:
            x, y, x1, y1 = speaker_box
            # Вычисляем центр лица спикера
            face_center_x = (x + x1) // 2
            face_center_y = (y + y1) // 2
            
            # Добавляем отступ вокруг лица
            face_height = y1 - y
            padding_y = int(face_height * padding_factor) // 2
            
            # Предпочитаемый центр кропа
            raw_crop_center_x = face_center_x
            raw_crop_center_y = max(face_center_y - padding_y, face_center_y)
        else:
            # По умолчанию центр кадра
            raw_crop_center_x = w // 2
            raw_crop_center_y = h // 2
        
        # 🎯 ПРИМЕНЯЕМ СГЛАЖИВАНИЕ ДЛЯ УМЕНЬШЕНИЯ ДЁРГАНЬЯ
        if use_smoothing:
            crop_center_x, crop_center_y = self._smooth_crop_center(
                (raw_crop_center_x, raw_crop_center_y)
            )
        else:
            crop_center_x, crop_center_y = raw_crop_center_x, raw_crop_center_y
        
        # Вычисляем размеры кропа с сохранением соотношения сторон
        if w / h > target_aspect:
            # Видео шире целевого - обрезаем по ширине
            crop_height = h
            crop_width = int(h * target_aspect)
        else:
            # Видео выше целевого - обрезаем по высоте
            crop_width = w
            crop_height = int(w / target_aspect)
        
        # Вычисляем границы кропа
        left = max(0, crop_center_x - crop_width // 2)
        right = min(w, left + crop_width)
        top = max(0, crop_center_y - crop_height // 2)
        bottom = min(h, top + crop_height)
        
        # Корректируем если область кропа выходит за границы
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
        
        # Выполняем кроп
        cropped = frame[top:bottom, left:right]
        
        # Изменяем размер до целевого разрешения
        if cropped.shape[:2] != (target_height, target_width):
            cropped = cv2.resize(cropped, target_size)
        
        return cropped

    def extract_audio_for_vad(self, video_path: Path) -> Optional[bytes]:
        """Extract audio from video for voice activity detection"""
        try:
            temp_audio_path = "temp_audio_vad.wav"
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
    
    def process_audio_frames(self, audio_data: bytes, sample_rate: int = 16000, frame_duration_ms: int = 30):
        """Generator for processing audio in chunks for VAD"""
        if not audio_data:
            return
        
        n = int(sample_rate * frame_duration_ms / 1000) * 2  # 2 bytes per sample
        offset = 0
        while offset + n <= len(audio_data):
            frame = audio_data[offset:offset + n]
            offset += n
            yield frame
    
    def create_vertical_crop(
        self, 
        input_video_path: Path, 
        output_video_path: Path,
        use_speaker_detection: bool = True,
        smoothing_strength: str = "very_high"
    ) -> bool:
        """
        Create a vertically cropped version of the video
        
        Args:
            input_video_path: Path to input video
            output_video_path: Path to save cropped video
            use_speaker_detection: Whether to use speaker detection for smart cropping
            smoothing_strength: Motion smoothing level ("low", "medium", "high", "very_high")
        """
        try:
            # Ensure output directory exists
            output_video_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Open video early to get properties
            cap = cv2.VideoCapture(str(input_video_path))
            if not cap.isOpened():
                logger.error(f"Could not open video: {input_video_path}")
                return False
            
            original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release() # Release now, will be reopened for processing

            # Calculate 9:16 width based on original height
            target_height = original_height
            target_width = int(original_height * (9 / 16))
            # Ensure width is even for compatibility
            if target_width % 2 != 0:
                target_width += 1
            target_size = (target_width, target_height)

            # 🎛️ КОНФИГУРАЦИЯ СГЛАЖИВАНИЯ
            smoothing_configs = {
                "low": {"smoothing_factor": 0.3, "max_jump_distance": 80, "stability_frames": 3},
                "medium": {"smoothing_factor": 0.75, "max_jump_distance": 50, "stability_frames": 5},
                "high": {"smoothing_factor": 0.9, "max_jump_distance": 25, "stability_frames": 8},
                "very_high": {"smoothing_factor": 0.95, "max_jump_distance": 15, "stability_frames": 12}
            }
            
            if smoothing_strength in smoothing_configs:
                config = smoothing_configs[smoothing_strength]
                self.smoothing_factor = config["smoothing_factor"]
                self.max_jump_distance = config["max_jump_distance"]
                self.stability_frames = config["stability_frames"]
                logger.info(f"🎛️ Using {smoothing_strength.upper()} smoothing:")
                logger.info(f"   └─ Factor: {config['smoothing_factor']}, Max jump: {config['max_jump_distance']}px, Frames: {config['stability_frames']}")
            else:
                logger.warning(f"⚠️ Unknown smoothing_strength '{smoothing_strength}', using 'medium'")
                config = smoothing_configs["medium"]
                self.smoothing_factor = config["smoothing_factor"]
                self.max_jump_distance = config["max_jump_distance"]
                self.stability_frames = config["stability_frames"]
            
            logger.info(f"🎬 Creating STABILIZED vertical crop: {target_size[0]}x{target_size[1]}")
            
            # 🎯 СБРАСЫВАЕМ СОСТОЯНИЕ СТАБИЛИЗАЦИИ ДЛЯ НОВОГО ВИДЕО
            self.previous_crop_center = None
            self.recent_centers = []
            
            # Extract audio for voice activity detection
            audio_data = None
            if use_speaker_detection and self.vad:
                audio_data = self.extract_audio_for_vad(input_video_path)
                logger.info("🔊 Audio extracted for voice activity detection")
            
            # Open video for processing
            cap = cv2.VideoCapture(str(input_video_path))
            if not cap.isOpened():
                logger.error(f"Could not open video: {input_video_path}")
                return False
            
            # Setup video writer for a temporary, silent video file
            temp_video_path = output_video_path.with_name(f"{output_video_path.stem}_temp.mp4")
            
            # Try multiple codecs for better compatibility
            codecs_to_try = [
                ('mp4v', 'MPEG-4'),
                ('XVID', 'Xvid'),
                ('avc1', 'H.264/AVC'),
                ('H264', 'H.264'),
                ('X264', 'x264')
            ]
            
            out = None
            used_codec = None
            
            for fourcc_str, codec_name in codecs_to_try:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
                    temp_out = cv2.VideoWriter(str(temp_video_path), fourcc, fps, target_size)
                    
                    # Test if the writer was created successfully
                    if temp_out.isOpened():
                        out = temp_out
                        used_codec = codec_name
                        logger.info(f"✅ Successfully created video writer with {codec_name} codec")
                        break
                    else:
                        temp_out.release()
                        logger.warning(f"⚠️ Failed to create video writer with {codec_name} codec")
                except Exception as e:
                    logger.warning(f"⚠️ Error with {codec_name} codec: {e}")
                    continue
            
            if out is None or not out.isOpened():
                logger.error("❌ Could not create video writer with any available codec")
                cap.release()
                return False
            
            # Setup audio processing
            audio_generator = None
            if audio_data:
                audio_generator = self.process_audio_frames(audio_data)
            
            frame_count = 0
            logger.info(f"📹 Processing {total_frames} frames with STABILIZATION...")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Get audio frame for VAD
                audio_frame = None
                if audio_generator:
                    try:
                        audio_frame = next(audio_generator)
                    except StopIteration:
                        audio_frame = None
                
                # Find active speaker
                speaker_box = None
                if use_speaker_detection:
                    speaker_box = self.find_active_speaker(frame, audio_frame)
                
                # Crop to vertical format with smoothing
                cropped_frame = self.crop_to_vertical(
                    frame, 
                    speaker_box, 
                    target_size,
                    use_smoothing=True  # 🎯 ВКЛЮЧАЕМ СГЛАЖИВАНИЕ
                )
                
                # Write frame
                out.write(cropped_frame)
                
                frame_count += 1
                if frame_count % (fps * 5) == 0:  # Progress every 5 seconds
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"📊 Stabilized progress: {progress:.1f}% ({frame_count}/{total_frames})")
            
            cap.release()
            out.release()
            
            logger.info("🎬 Silent vertical video created. Now adding audio via remuxing...")

            # --- AUDIO INTEGRATION STEP (Fast Remuxing) ---
            try:
                # First, check if the original video has an audio track
                with VideoFileClip(str(input_video_path)) as original_clip:
                    if original_clip.audio is None:
                        logger.warning("⚠️ Original video has no audio. The output will be silent.")
                        # If no audio, just rename the temp file to the final output
                        temp_video_path.rename(output_video_path)
                        return True

                # Use ffmpeg to copy streams without re-encoding (remuxing)
                # This is extremely fast and preserves 100% of the quality
                cmd = [
                    'ffmpeg',
                    '-hide_banner', '-loglevel', 'error',
                    '-i', str(temp_video_path),      # Input 0: our new silent vertical video
                    '-i', str(input_video_path),     # Input 1: the original video (for its audio)
                    '-c:v', 'copy',                  # Copy the video stream as is
                    '-c:a', 'copy',                  # Copy the audio stream as is
                    '-map', '0:v:0',                 # Map video from input 0
                    '-map', '1:a:0',                 # Map audio from input 1
                    '-shortest',                     # Finish when the shortest stream ends
                    str(output_video_path),
                    '-y'                             # Overwrite output file if it exists
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=False)

                if result.returncode == 0:
                    logger.info(f"✅ Audio successfully merged! Final video: {output_video_path}")
                    # Clean up the temporary silent video file
                    if temp_video_path.exists():
                        os.remove(temp_video_path)
                    return True
                else:
                    # If ffmpeg fails, log the error and fallback to the silent video
                    logger.error(f"❌ Failed to merge audio with ffmpeg: {result.stderr.strip()}")
                    if temp_video_path.exists():
                        temp_video_path.rename(output_video_path)
                        logger.warning(f"⚠️ Fallback: Saved SILENT video to {output_video_path}")
                    return False

            except Exception as e:
                logger.error(f"❌ An unexpected error occurred during audio merging: {e}")
                # If audio fails, provide the silent video as a fallback
                if temp_video_path.exists():
                    temp_video_path.rename(output_video_path)
                    logger.warning(f"⚠️ Fallback: Saved SILENT video to {output_video_path}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Vertical crop failed: {str(e)}")
            # Cleanup resources on failure
            if 'cap' in locals():
                cap.release()
            if 'out' in locals() and out is not None:
                out.release()
            if 'temp_video_path' in locals() and temp_video_path.exists():
                try:
                    os.remove(temp_video_path)
                except:
                    pass  # Ignore cleanup errors
            return False

# Global service instance
vertical_crop_service = VerticalCropService()

# Convenience functions for integration
def crop_video_to_vertical(
    input_path: Path, 
    output_path: Path, 
    use_speaker_detection: bool = True,
    smoothing_strength: str = "very_high"
) -> bool:
    """
    Convenience function to crop a video to vertical format with motion smoothing
    
    Args:
        input_path: Path to input video
        output_path: Path to save cropped video
        use_speaker_detection: Whether to use speaker detection for smart cropping
        smoothing_strength: Motion smoothing level:
            - "low": Минимальное сглаживание (быстрая реакция, factor=0.3, jump=80px)
            - "medium": Среднее сглаживание (баланс, factor=0.75, jump=50px) 
            - "high": Максимальное сглаживание (очень плавно, factor=0.9, jump=25px)
            - "very_high": Экстремальное сглаживание (максимально плавно, factor=0.95, jump=30px)
    """
    return vertical_crop_service.create_vertical_crop(
        input_path, 
        output_path, 
        use_speaker_detection, 
        smoothing_strength
    )

def process_video_to_vertical_shorts(input_video_path, output_video_path, target_width=608, target_height=1080):
    """
    Process entire video to create vertical shorts format
    """
    # Extract audio for voice activity detection
    extract_audio_from_video(input_video_path, "temp_audio.wav")
    
    # Read audio data
    with contextlib.closing(wave.open("temp_audio.wav", 'rb')) as wf:
        sample_rate = wf.getframerate()
        audio_data = wf.readframes(wf.getnframes())
    
    cap = cv2.VideoCapture(input_video_path)
    
    # Get original video properties
    original_fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Setup video writer for output
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, original_fps, (target_width, target_height))
    
    frame_duration_ms = 30  # 30ms audio frames
    audio_generator = process_audio_frame(audio_data, sample_rate, frame_duration_ms)
    
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Get corresponding audio frame
        audio_frame = next(_generator, None)
        if audio_frame is None:
            # Pad with silence if audio is shorter
            audio_frame = b'\x00' * (int(sample_rate * frame_duration_ms / 1000) * 2)
        
        # Detect active speaker
        speaker_box = detect_active_speaker(frame, audio_frame)
        
        # Crop to vertical format
        cropped_frame = crop_to_vertical_shorts(frame, speaker_box, target_width, target_height)
        
        # Write frame
        out.write(cropped_frame)
        
        frame_count += 1
        if frame_count % 30 == 0:  # Progress every second
            print(f"Processed {frame_count}/{total_frames} frames")
    
    cap.release()
    out.release()
    
    # Clean up temp audio file
    os.remove("temp_audio.wav")
    
    print(f"Vertical shorts video saved to: {output_video_path}")

def crop_to_vertical_shorts(frame, speaker_box, target_width=608, target_height=1080):
    """
    Crop frame to 9:16 aspect ratio centered on the active speaker
    Standard YouTube Shorts resolution: 608x1080 or 1080x1920
    """
    h, w = frame.shape[:2]
    
    if speaker_box:
        # Calculate center of speaker's face
        x, y, x1, y1 = speaker_box
        face_center_x = (x + x1) // 2
        face_center_y = (y + y1) // 2
    else:
        # Default to center of frame if no speaker detected
        face_center_x = w // 2
        face_center_y = h // 2
    
    # Calculate crop boundaries
    crop_width = target_width
    crop_height = target_height
    
    # Ensure crop doesn't exceed frame boundaries
    if crop_width > w:
        crop_width = w
    if crop_height > h:
        crop_height = h
    
    # Calculate crop coordinates centered on speaker
    left = max(0, face_center_x - crop_width // 2)
    right = min(w, left + crop_width)
    top = max(0, face_center_y - crop_height // 2)
    bottom = min(h, top + crop_height)
    
    # Adjust if crop area is at boundary
    if right - left < crop_width:
        if left == 0:
            right = crop_width
        else:
            left = w - crop_width
    
    if bottom - top < crop_height:
        if top == 0:
            bottom = crop_height
        else:
            top = h - crop_height
    
    # Crop the frame
    cropped_frame = frame[top:bottom, left:right]
    
    # Resize to target resolution maintaining aspect ratio
    cropped_frame = cv2.resize(cropped_frame, (target_width, target_height))
    
    return cropped_frame

def extract_audio_from_video(video_path, audio_path):
    """Extract audio from video for voice activity detection"""
    audio = AudioSegment.from_file(video_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(audio_path, format="wav")

def process_audio_frame(audio_data, sample_rate=16000, frame_duration_ms=30):
    """Generator for processing audio in chunks"""
    n = int(sample_rate * frame_duration_ms / 1000) * 2  # 2 bytes per sample
    offset = 0
    while offset + n <= len(audio_data):
        frame = audio_data[offset:offset + n]
        offset += n
        yield frame 