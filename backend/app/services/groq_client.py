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
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        self.client = groq.Groq(api_key=self.api_key)
        self.model = "whisper-large-v3"
        self.max_file_size_mb = 25  # Groq's file size limit

    def _check_file_size(self, file_path: str) -> float:
        """Check file size in MB.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            File size in MB
        """
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        return file_size_mb

    def _split_audio_into_chunks(self, file_path: str, task_id: Optional[str] = None) -> List[str]:
        """Split large audio file into chunks under the size limit.
        
        Args:
            file_path: Path to the audio file to split
            task_id: Task ID for logging
            
        Returns:
            List of paths to audio chunk files
        """
        try:
            logger.info(f"🔧 Splitting large audio file into chunks (task_id: {task_id})")
            
            # Load the audio file
            audio = AudioSegment.from_file(file_path)
            duration_ms = len(audio)
            duration_seconds = duration_ms / 1000
            
            # Calculate how many chunks we need based on file size
            file_size_mb = self._check_file_size(file_path)
            num_chunks = int((file_size_mb / self.max_file_size_mb) + 1)
            
            # Calculate chunk duration
            chunk_duration_ms = duration_ms // num_chunks
            
            logger.info(f"📊 Audio splitting: {duration_seconds:.1f}s total, {file_size_mb:.1f}MB, splitting into {num_chunks} chunks")
            
            chunk_paths = []
            base_path = Path(file_path)
            
            for i in range(num_chunks):
                start_ms = i * chunk_duration_ms
                
                # For the last chunk, include any remaining audio
                if i == num_chunks - 1:
                    end_ms = duration_ms
                else:
                    end_ms = (i + 1) * chunk_duration_ms
                
                # Extract chunk
                chunk = audio[start_ms:end_ms]
                
                # Save chunk
                chunk_path = str(base_path.parent / f"{base_path.stem}_chunk_{i+1}{base_path.suffix}")
                chunk.export(chunk_path, format="wav")
                
                chunk_size_mb = self._check_file_size(chunk_path)
                chunk_duration_s = len(chunk) / 1000
                
                logger.info(f"✅ Created chunk {i+1}/{num_chunks}: {chunk_duration_s:.1f}s, {chunk_size_mb:.1f}MB")
                chunk_paths.append(chunk_path)
            
            return chunk_paths
            
        except Exception as e:
            logger.error(f"❌ Failed to split audio file: {str(e)}")
            raise TranscriptionError(f"Audio splitting failed: {str(e)}", task_id=task_id)

    def _merge_transcription_results(self, chunk_results: List[Dict[str, Any]], task_id: Optional[str] = None) -> Dict[str, Any]:
        """Merge transcription results from multiple chunks.
        
        Args:
            chunk_results: List of transcription results from each chunk
            task_id: Task ID for logging
            
        Returns:
            Merged transcription result
        """
        try:
            logger.info(f"🔧 Merging {len(chunk_results)} chunk transcription results (task_id: {task_id})")
            
            merged_segments = []
            merged_word_timestamps = []
            total_cost = 0
            total_latency = 0
            
            # Use language from first chunk (they should all be the same)
            language = chunk_results[0]["language"] if chunk_results else "unknown"
            
            # Keep track of time offset as we merge chunks
            time_offset = 0.0
            
            for i, result in enumerate(chunk_results):
                chunk_segments = result.get("segments", [])
                chunk_words = result.get("word_timestamps", [])
                
                # Adjust timestamps by adding the offset
                for segment in chunk_segments:
                    if hasattr(segment, 'start'):
                        segment.start += time_offset
                        segment.end += time_offset
                    elif isinstance(segment, dict):
                        segment['start'] = segment.get('start', 0) + time_offset
                        segment['end'] = segment.get('end', 0) + time_offset
                
                for word in chunk_words:
                    if hasattr(word, 'start'):
                        word.start += time_offset
                        word.end += time_offset
                    elif isinstance(word, dict):
                        word['start'] = word.get('start', 0) + time_offset
                        word['end'] = word.get('end', 0) + time_offset
                
                merged_segments.extend(chunk_segments)
                merged_word_timestamps.extend(chunk_words)
                
                # Update time offset for next chunk
                if chunk_segments:
                    last_segment = chunk_segments[-1]
                    if hasattr(last_segment, 'end'):
                        time_offset = last_segment.end
                    elif isinstance(last_segment, dict):
                        time_offset = last_segment.get('end', time_offset)
                
                # Accumulate costs and latency
                total_cost += result.get("cost_usd", 0)
                total_latency += result.get("latency_ms", 0)
            
            logger.info(f"✅ Merged transcription: {len(merged_segments)} segments, {len(merged_word_timestamps)} words")
            
            return {
                "segments": merged_segments,
                "word_timestamps": merged_word_timestamps,
                "language": language,
                "cost_usd": round(total_cost, 4),
                "latency_ms": total_latency
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to merge transcription results: {str(e)}")
            raise TranscriptionError(f"Result merging failed: {str(e)}", task_id=task_id)

    def _cleanup_chunks(self, chunk_paths: List[str]) -> None:
        """Clean up temporary chunk files.
        
        Args:
            chunk_paths: List of paths to chunk files to delete
        """
        for chunk_path in chunk_paths:
            try:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    logger.debug(f"🧹 Cleaned up chunk: {chunk_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up chunk {chunk_path}: {e}")
    
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
            
            # Check file size and use chunking if necessary
            file_size_mb = self._check_file_size(processed_file_path)
            logger.info(f"📊 Audio file size: {file_size_mb:.1f}MB (limit: {self.max_file_size_mb}MB)")
            
            if file_size_mb > self.max_file_size_mb:
                logger.info(f"🔧 File exceeds size limit, using chunking approach")
                return self._transcribe_with_chunking(processed_file_path, language, task_id, apply_vad, file_path, start_time)
            else:
                logger.info(f"✅ File size OK, using direct transcription")
                return self._transcribe_single_file(processed_file_path, language, task_id, apply_vad, file_path, start_time)
            
        except Exception as e:
            logger.error(f"Transcription failed (task_id: {task_id}): {str(e)}")
            raise TranscriptionError(f"Transcription failed: {str(e)}", task_id=task_id)

    def _transcribe_single_file(
        self, 
        processed_file_path: str, 
        language: Optional[str], 
        task_id: Optional[str], 
        apply_vad: bool, 
        original_file_path: str, 
        start_time: float
    ) -> Dict[str, Any]:
        """Transcribe a single audio file (under the size limit).
        
        Args:
            processed_file_path: Path to processed audio file
            language: Language code
            task_id: Task ID for logging
            apply_vad: Whether VAD was applied
            original_file_path: Original file path before VAD
            start_time: Start time for latency calculation
            
        Returns:
            Transcription result dictionary
        """
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
        if apply_vad and processed_file_path != original_file_path:
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

    def _transcribe_with_chunking(
        self, 
        processed_file_path: str, 
        language: Optional[str], 
        task_id: Optional[str], 
        apply_vad: bool, 
        original_file_path: str, 
        start_time: float
    ) -> Dict[str, Any]:
        """Transcribe a large audio file by splitting it into chunks.
        
        Args:
            processed_file_path: Path to processed audio file
            language: Language code
            task_id: Task ID for logging
            apply_vad: Whether VAD was applied
            original_file_path: Original file path before VAD
            start_time: Start time for latency calculation
            
        Returns:
            Merged transcription result dictionary
        """
        chunk_paths = []
        
        try:
            # Split audio into chunks
            chunk_paths = self._split_audio_into_chunks(processed_file_path, task_id)
            
            # Transcribe each chunk
            chunk_results = []
            for i, chunk_path in enumerate(chunk_paths):
                logger.info(f"🎤 Transcribing chunk {i+1}/{len(chunk_paths)}: {chunk_path}")
                
                chunk_result = self._transcribe_single_file(
                    processed_file_path=chunk_path,
                    language=language,
                    task_id=f"{task_id}_chunk_{i+1}",
                    apply_vad=False,  # VAD already applied to main file
                    original_file_path=chunk_path,
                    start_time=time.time()  # Individual chunk timing
                )
                
                chunk_results.append(chunk_result)
                logger.info(f"✅ Chunk {i+1} transcribed: {len(chunk_result['segments'])} segments")
            
            # Merge results
            merged_result = self._merge_transcription_results(chunk_results, task_id)
            
            # Update overall latency
            overall_latency_ms = int((time.time() - start_time) * 1000)
            merged_result["latency_ms"] = overall_latency_ms
            
            logger.info(f"🎉 Chunked transcription completed: {len(merged_result['segments'])} total segments")
            
            # Clean up VAD-filtered file if created
            if apply_vad and processed_file_path != original_file_path:
                try:
                    os.remove(processed_file_path)
                except OSError:
                    logger.warning(f"Failed to clean up VAD-filtered file: {processed_file_path}")
            
            return merged_result
            
        finally:
            # Always clean up chunk files
            if chunk_paths:
                self._cleanup_chunks(chunk_paths)


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