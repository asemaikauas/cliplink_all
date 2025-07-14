"""Groq Whisper client wrapper with VAD pre-filtering."""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


from dotenv import load_dotenv

load_dotenv()
import groq
from pydub import AudioSegment
from pydub.silence import detect_silence

from app.exceptions import TranscriptionError, VADError


logger = logging.getLogger(__name__)


class GroqClient:
    """Groq Whisper large-v3 client with VAD pre-filtering."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Groq client.
        
        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
        """
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise TranscriptionError("GROQ_API_KEY not found in environment variables")
        
        try:
            # Try standard initialization
            self.client = groq.Groq(api_key=self.api_key)
        except TypeError as e:
            if "proxies" in str(e):
                # Handle version compatibility issue with proxies argument
                logger.warning(f"Groq client initialization error (proxies issue): {e}")
                try:
                    # Try without any extra arguments
                    self.client = groq.Groq(api_key=self.api_key, http_client=None)
                except:
                    # Final fallback - try with minimal args
                    logger.warning("Using fallback Groq client initialization")
                    self.client = groq.Groq(api_key=self.api_key, base_url="https://api.groq.com")
            else:
                raise e
        
        self.model = "whisper-large-v3"
    
    def _apply_vad_filtering(
        self, 
        audio_path: str, 
        silence_threshold: int = None,
        min_silence_duration: int = None
    ) -> str:
        """Apply Voice Activity Detection to remove silent stretches.
        
        Args:
            audio_path: Path to input audio file
            silence_threshold: Silence threshold in dB (default from env or -55 dB)
            min_silence_duration: Minimum silence duration in ms (default from env or 5000 ms)
            
        Returns:
            Path to processed audio file with silence removed
            
        Raises:
            VADError: If VAD processing fails
        """
        try:
            # Use environment variables for defaults if not provided
            if silence_threshold is None:
                silence_threshold = int(os.getenv("VAD_SILENCE_THRESHOLD", -55))
            if min_silence_duration is None:
                min_silence_duration = int(os.getenv("VAD_MIN_SILENCE_DURATION", 5000))
                
            logger.info(f"Applying VAD filtering to {audio_path} (threshold: {silence_threshold}dB, min_duration: {min_silence_duration}ms)")
            
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            
            # Detect silent segments
            silent_segments = detect_silence(
                audio,
                min_silence_len=min_silence_duration,
                silence_thresh=silence_threshold
            )
            
            logger.info(f"Found {len(silent_segments)} silent segments to remove")
            
            # Calculate total duration being removed
            total_removed_ms = sum(end - start for start, end in silent_segments)
            original_duration_ms = len(audio)
            
            logger.info(f"VAD will remove {total_removed_ms/1000:.1f}s of silence from {original_duration_ms/1000:.1f}s audio ({total_removed_ms/original_duration_ms*100:.1f}%)")
            
            # Warn if removing too much content
            if total_removed_ms / original_duration_ms > 0.5:
                logger.warning(f"⚠️ VAD is removing >50% of audio content! Consider disabling VAD or adjusting parameters.")
            
            # Remove silent segments (in reverse order to maintain indices)
            for start, end in reversed(silent_segments):
                logger.debug(f"Removing silence from {start}ms to {end}ms")
                audio = audio[:start] + audio[end:]
            
            # Export processed audio
            audio_path_obj = Path(audio_path)
            output_path = str(audio_path_obj.parent / f"{audio_path_obj.stem}_vad_filtered.wav")
            
            audio.export(output_path, format="wav")
            
            logger.info(f"VAD filtered audio saved to {output_path}")
            return output_path
            
        except Exception as e:
            raise VADError(f"VAD filtering failed: {str(e)}")
    
    def transcribe(
        self,
        file_path: str,
        apply_vad: bool = False,
        language: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe audio file using Groq Whisper large-v3.
        
        Args:
            file_path: Path to audio/video file
            apply_vad: Whether to apply VAD pre-filtering
            language: Language code (optional, auto-detect if None)
            task_id: Task ID for logging
            
        Returns:
            Dictionary containing:
                - segments: List of transcription segments with word-level timestamps
                - language: Detected language code
                - cost_usd: Estimated cost in USD
                - latency_ms: Processing latency in milliseconds
                
        Raises:
            TranscriptionError: If transcription fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting transcription for {file_path} (task_id: {task_id})")
            
            # Apply VAD filtering if requested
            processed_file_path = file_path
            if apply_vad:
                processed_file_path = self._apply_vad_filtering(file_path)
            
            # Open and transcribe the audio file
            with open(processed_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.model,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"],  # Ask for both segments and words
                    language=language
                )
            
            # Debug: Print what we got from Groq including word-level data
            print(f"\n🔍 DEBUG - Groq Response for task {task_id}:")
            print(f"   Has segments attr: {hasattr(transcription, 'segments')}")
            print(f"   Segments is None: {getattr(transcription, 'segments', 'NO_ATTR') is None}")
            print(f"   Has words attr: {hasattr(transcription, 'words')}")
            print(f"   Words is None: {getattr(transcription, 'words', 'NO_ATTR') is None}")
            print(f"   Has text attr: {hasattr(transcription, 'text')}")
            print(f"   Text content: {getattr(transcription, 'text', 'NO_TEXT')[:100] if hasattr(transcription, 'text') else 'NO_TEXT'}...")
            print(f"   Language: {getattr(transcription, 'language', 'NO_LANGUAGE')}")
            
            if hasattr(transcription, 'segments') and transcription.segments:
                print(f"   Segments count: {len(transcription.segments)}")
                print(f"   First segment type: {type(transcription.segments[0])}")
                print(f"   First segment content: {transcription.segments[0] if transcription.segments else 'NO_SEGMENTS'}")
                if transcription.segments and isinstance(transcription.segments[0], dict):
                    print(f"   First segment keys: {list(transcription.segments[0].keys())}")
            
            if hasattr(transcription, 'words') and transcription.words:
                print(f"   Words count: {len(transcription.words)}")
                print(f"   First word type: {type(transcription.words[0])}")
                print(f"   First 3 words: {transcription.words[:3] if transcription.words else 'NO_WORDS'}")
                if transcription.words and isinstance(transcription.words[0], dict):
                    print(f"   First word keys: {list(transcription.words[0].keys())}")
            elif hasattr(transcription, 'segments') and transcription.segments:
                # Check if words are nested in segments
                first_segment = transcription.segments[0]
                if isinstance(first_segment, dict) and 'words' in first_segment:
                    print(f"   Words nested in segments - first segment words: {len(first_segment['words'])} words")
                    print(f"   First word in segment: {first_segment['words'][0] if first_segment['words'] else 'NO_WORDS'}")
            
            print() # Empty line for readability
            
            # Extract both segments and word-level timing data
            if not hasattr(transcription, 'segments'):
                logger.warning(f"Transcription response missing segments attribute (task_id: {task_id})")
                segments = []
            elif transcription.segments is None:
                logger.warning(f"Transcription segments is None (task_id: {task_id})")
                segments = []
            else:
                segments = transcription.segments
            
            # Extract word-level timestamps for speech synchronization
            word_timestamps = []
            
            # Method 1: Check for top-level words attribute
            if hasattr(transcription, 'words') and transcription.words:
                logger.info(f"Found {len(transcription.words)} word-level timestamps")
                word_timestamps = transcription.words
            # Method 2: Extract words from segments
            elif segments:
                logger.info("Extracting word timestamps from segments")
                for segment in segments:
                    if isinstance(segment, dict) and 'words' in segment and segment['words']:
                        word_timestamps.extend(segment['words'])
                    elif hasattr(segment, 'words') and segment.words:
                        word_timestamps.extend(segment.words)
                
                logger.info(f"Extracted {len(word_timestamps)} word-level timestamps from segments")
            
            if word_timestamps:
                # Debug: show first few word timestamps
                logger.info(f"🎯 Word-level timing sample: {word_timestamps[:5]}")
            
            # Validate language
            language_code = getattr(transcription, 'language', 'unknown')
            if not language_code:
                language_code = 'unknown'
            
            # Calculate metrics
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Estimate cost (Groq pricing: ~$0.111 per hour of audio)
            # Use actual audio duration for more accurate cost estimation
            try:
                from pydub import AudioSegment
                audio_segment = AudioSegment.from_file(processed_file_path)
                duration_hours = audio_segment.duration_seconds / 3600
                cost_usd = duration_hours * 0.111
            except Exception:
                # Fallback to file size estimation if audio loading fails
                file_size_mb = os.path.getsize(processed_file_path) / (1024 * 1024)
                estimated_duration_hours = file_size_mb / 10  # Rough estimate
                cost_usd = estimated_duration_hours * 0.111
            
            # Print transcribed text to console
            full_text = ""
            if segments:
                # Handle both dictionary and object formats
                text_parts = []
                for segment in segments:
                    if isinstance(segment, dict):
                        text = segment.get('text', '').strip()
                    else:
                        text = getattr(segment, 'text', '').strip()
                    if text:
                        text_parts.append(text)
                full_text = " ".join(text_parts)
            elif hasattr(transcription, 'text') and transcription.text:
                full_text = transcription.text
            
            if full_text:
                print("\n" + "="*80)
                print(f"🎤 TRANSCRIBED TEXT (Task: {task_id})")
                print("="*80)
                print(full_text)
                print("="*80 + "\n")
            else:
                print(f"\n⚠️  No transcribed text found for task {task_id}\n")
            
            logger.info(
                f"Transcription completed (task_id: {task_id}) - "
                f"language: {language_code}, "
                f"segments: {len(segments)}, "
                f"latency: {latency_ms}ms, "
                f"estimated_cost: ${cost_usd:.4f}"
            )
            
            # Validate that we have some content
            if len(segments) == 0:
                logger.warning(f"No transcription segments found (task_id: {task_id})")
                # Check if there's text content in the response
                if hasattr(transcription, 'text') and transcription.text:
                    logger.info(f"Found transcription text but no segments, creating fallback segment")
                    # Create a simple segment from the full text
                    from types import SimpleNamespace
                    fallback_segment = SimpleNamespace()
                    fallback_segment.start = 0.0
                    fallback_segment.end = 30.0  # Longer default duration
                    fallback_segment.text = transcription.text
                    segments = [fallback_segment]
                    
                    # Try to split into smaller segments based on sentences
                    import re
                    sentences = re.split(r'[.!?]+', transcription.text)
                    if len(sentences) > 1:
                        segments = []
                        duration_per_sentence = 30.0 / len(sentences)
                        for i, sentence in enumerate(sentences):
                            if sentence.strip():
                                segment = SimpleNamespace()
                                segment.start = i * duration_per_sentence
                                segment.end = (i + 1) * duration_per_sentence
                                segment.text = sentence.strip()
                                segments.append(segment)
                        logger.info(f"Split text into {len(segments)} sentence-based segments")
                else:
                    logger.warning(f"No transcription content found at all (task_id: {task_id})")
            
            # Clean up VAD-filtered file if created
            if apply_vad and processed_file_path != file_path:
                try:
                    os.remove(processed_file_path)
                except OSError:
                    logger.warning(f"Failed to clean up VAD-filtered file: {processed_file_path}")
            
            return {
                "segments": segments,
                "word_timestamps": word_timestamps,  # Add word-level timing for speech sync
                "language": language_code,
                "cost_usd": round(cost_usd, 4),
                "latency_ms": latency_ms
            }
            
        except Exception as e:
            logger.error(f"Transcription failed (task_id: {task_id}): {str(e)}")
            raise TranscriptionError(f"Transcription failed: {str(e)}", task_id=task_id)


def transcribe(
    file_path: str,
    apply_vad: bool = False,
    language: Optional[str] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function to transcribe audio file.
    
    Args:
        file_path: Path to audio/video file
        apply_vad: Whether to apply VAD pre-filtering
        language: Language code (optional, auto-detect if None)
        task_id: Task ID for logging
        
    Returns:
        Dictionary containing segments, language, cost_usd, latency_ms
    """
    client = GroqClient()
    return client.transcribe(file_path, apply_vad, language, task_id) 