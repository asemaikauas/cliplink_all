"""Subtitle post-processor for converting Groq segments to SRT and VTT."""

import re
import logging
import sys
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from app.exceptions import SubtitleFormatError


logger = logging.getLogger(__name__)


@dataclass
class SubtitleSegment:
    """A subtitle segment with text and timing."""
    start_time: float
    end_time: float
    text: str
    
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end_time - self.start_time


class SubtitleProcessor:
    """Process transcription segments into subtitle formats."""
    
    def __init__(
        self,
        max_chars_per_line: int = 50,  # Legacy parameter - not used in CapCut mode
        max_lines: int = 2,  # Legacy parameter - not used in CapCut mode  
        merge_gap_threshold_ms: int = 200,
        capcut_mode: bool = True,  # Enable CapCut-style punch words
        speech_sync_mode: bool = False,  # Enable true speech synchronization using word timestamps
        min_word_duration_ms: int = 800,  # Minimum display time per word chunk
        max_word_duration_ms: int = 1500,  # Maximum display time per word chunk
        word_overlap_ms: int = 150  # Overlap between word chunks for smooth flow
    ):
        """Initialize subtitle processor.
        
        Args:
            max_chars_per_line: Maximum characters per subtitle line (legacy)
            max_lines: Maximum number of lines per subtitle (legacy)
            merge_gap_threshold_ms: Merge segments with gaps smaller than this (ms)
            capcut_mode: Enable CapCut-style adaptive word chunks
            speech_sync_mode: Enable true speech synchronization using word timestamps
            min_word_duration_ms: Minimum display time per word chunk (ms)
            max_word_duration_ms: Maximum display time per word chunk (ms)  
            word_overlap_ms: Overlap between word chunks for smooth transitions (ms)
        """
        self.max_chars_per_line = max_chars_per_line
        self.max_lines = max_lines
        self.merge_gap_threshold_ms = merge_gap_threshold_ms
        self.capcut_mode = capcut_mode
        self.speech_sync_mode = speech_sync_mode
        self.min_word_duration_ms = min_word_duration_ms
        self.max_word_duration_ms = max_word_duration_ms
        self.word_overlap_ms = word_overlap_ms
    
    def _merge_micro_gaps(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Merge segments with micro-gaps smaller than threshold.
        
        Args:
            segments: List of subtitle segments
            
        Returns:
            List of merged subtitle segments
        """
        if not segments:
            return segments
        
        merged = [segments[0]]
        merge_threshold_s = self.merge_gap_threshold_ms / 1000.0
        
        for current in segments[1:]:
            previous = merged[-1]
            gap = current.start_time - previous.end_time
            
            # If gap is smaller than threshold, merge segments
            if gap <= merge_threshold_s:
                logger.debug(
                    f"Merging segments with {gap*1000:.1f}ms gap: "
                    f"'{previous.text}' + '{current.text}'"
                )
                merged[-1] = SubtitleSegment(
                    start_time=previous.start_time,
                    end_time=current.end_time,
                    text=f"{previous.text} {current.text}"
                )
            else:
                merged.append(current)
        
        logger.info(f"Merged {len(segments)} segments into {len(merged)} segments")
        return merged
    
    def _wrap_text(self, text: str) -> Tuple[List[str], str]:
        """Wrap text to meet line length and count constraints.
        
        Args:
            text: Text to wrap
            
        Returns:
            Tuple of (wrapped_lines, remaining_text)
        """
        words = text.split()
        lines = []
        current_line = ""
        remaining_words = []
        
        for i, word in enumerate(words):
            # Check if adding this word would exceed line length
            test_line = f"{current_line} {word}".strip()
            
            if len(test_line) <= self.max_chars_per_line:
                current_line = test_line
            else:
                # Start new line
                if current_line:
                    lines.append(current_line)
                current_line = word
                
                # If we've reached max lines, save remaining words starting from NEXT word
                if len(lines) >= self.max_lines:
                    # Current word goes in current_line, remaining starts from next word
                    remaining_words = words[i + 1:]  # Start from NEXT word, not current
                    break
        
        # Add the last line if we haven't exceeded max lines
        if current_line and len(lines) < self.max_lines:
            lines.append(current_line)
        elif current_line and len(lines) >= self.max_lines:
            # If we have a current line but reached max lines, add it to remaining
            remaining_words = [current_line] + remaining_words
        
        remaining_text = " ".join(remaining_words) if remaining_words else ""
        
        return lines, remaining_text
    
    def _create_capcut_word_chunks(self, text: str, start_time: float, end_time: float) -> List[SubtitleSegment]:
        """Create CapCut-style word chunks with millisecond precision timing.
        
        Args:
            text: Text to chunk into punch words
            start_time: Original segment start time (seconds)
            end_time: Original segment end time (seconds)
            
        Returns:
            List of word chunk segments with overlapping timing
        """
        words = text.split()
        if not words:
            return []
        
        duration_s = end_time - start_time
        duration_ms = duration_s * 1000
        
        # Create adaptive chunks based on natural speech patterns and punctuation
        chunks = []
        i = 0
        while i < len(words):
            remaining_words = len(words) - i
            
            # Look ahead for natural breaking points (punctuation, conjunctions)
            natural_break_found = False
            optimal_chunk_size = 3  # Default fallback
            
            # Check for natural breaks within next 3-6 words
            for look_ahead in range(3, min(7, remaining_words + 1)):
                if i + look_ahead <= len(words):
                    # Check the word at this position for natural break indicators
                    if i + look_ahead < len(words):
                        next_word = words[i + look_ahead - 1].lower()
                        
                        # Natural break indicators
                        if (next_word.endswith(('.', ',', '!', '?', ':', ';')) or 
                            next_word in ['and', 'but', 'or', 'so', 'then', 'now', 'well', 'because', 'since', 'while', 'when', 'where', 'how', 'that', 'which', 'who']):
                            optimal_chunk_size = look_ahead
                            natural_break_found = True
                            break
            
            # If no natural break found, use adaptive sizing based on content
            if not natural_break_found:
                if remaining_words >= 8:
                    # Longer content: prefer 5-word chunks
                    optimal_chunk_size = 5
                elif remaining_words >= 6:
                    # Medium content: prefer 4-word chunks  
                    optimal_chunk_size = 4
                elif remaining_words >= 4:
                    # Shorter content: use all remaining or split evenly
                    if remaining_words == 4:
                        optimal_chunk_size = 4
                    elif remaining_words == 5:
                        optimal_chunk_size = 3  # 3+2 split
                    elif remaining_words == 6:
                        optimal_chunk_size = 3  # 3+3 split
                    elif remaining_words == 7:
                        optimal_chunk_size = 4  # 4+3 split
                else:
                    # Very short: use all remaining
                    optimal_chunk_size = remaining_words
            
            # Ensure we don't exceed remaining words
            chunk_size = min(optimal_chunk_size, remaining_words)
            
            chunk_words = words[i:i+chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)
            i += chunk_size
            
            logger.debug(f"Chunk: '{chunk_text}' (size: {chunk_size}, natural_break: {natural_break_found})")
        
        if not chunks:
            return []
        
        logger.debug(f"CapCut chunking: '{text}' -> {len(chunks)} chunks: {chunks}")
        
        # Calculate timing for each chunk with millisecond precision
        segments = []
        overlap_ms = self.word_overlap_ms
        min_duration_ms = self.min_word_duration_ms
        max_duration_ms = self.max_word_duration_ms
        
        if len(chunks) == 1:
            # Single chunk gets full duration, capped at max
            chunk_duration_ms = min(max_duration_ms, duration_ms)
            chunk_start_ms = start_time * 1000
            chunk_end_ms = chunk_start_ms + chunk_duration_ms
            
            segments.append(SubtitleSegment(
                start_time=chunk_start_ms / 1000.0,
                end_time=chunk_end_ms / 1000.0,
                text=chunks[0]
            ))
        else:
            # Multiple chunks with simple sequential timing (no overlaps)
            total_duration_s = duration_s
            
            # Simple approach: equal time distribution with minimum duration respect
            base_duration_s = total_duration_s / len(chunks)
            
            # Ensure base duration meets minimum requirement
            min_duration_s = min_duration_ms / 1000.0
            max_duration_s = max_duration_ms / 1000.0
            
            # If base duration is too short, use minimum and adjust total
            if base_duration_s < min_duration_s:
                base_duration_s = min_duration_s
            elif base_duration_s > max_duration_s:
                base_duration_s = max_duration_s
            
            current_start_s = start_time
            
            for i, chunk_text in enumerate(chunks):
                chunk_start_s = current_start_s
                
                if i == len(chunks) - 1:
                    # Last chunk: end exactly at original end time
                    chunk_end_s = end_time
                else:
                    # Regular chunk: use calculated duration
                    chunk_end_s = chunk_start_s + base_duration_s
                    
                    # Safety check: ensure we don't exceed original end time
                    if chunk_end_s > end_time:
                        chunk_end_s = end_time
                
                # Safety check: ensure positive duration
                if chunk_end_s <= chunk_start_s:
                    chunk_end_s = chunk_start_s + min_duration_s
                
                segments.append(SubtitleSegment(
                    start_time=chunk_start_s,
                    end_time=chunk_end_s,
                    text=chunk_text
                ))
                
                # Next chunk starts exactly when current chunk ends
                current_start_s = chunk_end_s
                
                # Safety check: if we've reached the end, stop
                if current_start_s >= end_time:
                    break
        
        logger.debug(f"CapCut timing: {len(segments)} sequential segments (no overlaps)")
        
        return segments
    
    def _create_speech_sync_chunks(self, word_timestamps: List[Any]) -> List[SubtitleSegment]:
        """Create speech-synchronized chunks using actual word timing from Groq.
        
        Args:
            word_timestamps: List of word objects with start/end timing from Groq
            
        Returns:
            List of subtitle segments with true speech timing
        """
        if not word_timestamps:
            logger.warning("No word timestamps provided for speech sync")
            return []
        
        segments = []
        min_duration_s = self.min_word_duration_ms / 1000.0
        max_duration_s = self.max_word_duration_ms / 1000.0
        
        # Process words and group them into natural chunks
        current_chunk_words = []
        current_chunk_start = None
        current_chunk_end = None
        
        logger.info(f"🎯 Creating speech-sync chunks from {len(word_timestamps)} words")
        
        for i, word_obj in enumerate(word_timestamps):
            # Extract word data (handle both dict and object formats)
            if isinstance(word_obj, dict):
                word_text = word_obj.get('word', '').strip()
                word_start = float(word_obj.get('start', 0))
                word_end = float(word_obj.get('end', 0))
            else:
                word_text = getattr(word_obj, 'word', '').strip()
                word_start = float(getattr(word_obj, 'start', 0))
                word_end = float(getattr(word_obj, 'end', 0))
            
            if not word_text:
                continue
            
            # Start new chunk if this is the first word
            if current_chunk_start is None:
                current_chunk_start = word_start
                current_chunk_words = [word_text]
                current_chunk_end = word_end
                continue
            
            # Calculate current chunk duration if we add this word
            potential_duration = word_end - current_chunk_start
            current_text_length = len(" ".join(current_chunk_words + [word_text]))
            
            # Decide whether to add word to current chunk or start new chunk
            should_break = False
            
            # Break conditions:
            # 1. Chunk would be too long (over max duration)
            if potential_duration > max_duration_s:
                should_break = True
                logger.debug(f"Breaking chunk due to max duration: {potential_duration:.2f}s > {max_duration_s:.2f}s")
            
            # 2. Too much text for readability (over 50 characters)
            elif current_text_length > 50:
                should_break = True
                logger.debug(f"Breaking chunk due to text length: {current_text_length} chars")
            
            # 3. Natural break points (punctuation)
            elif (current_chunk_words and 
                  any(current_chunk_words[-1].endswith(p) for p in ['.', ',', '!', '?', ':', ';'])):
                should_break = True
                logger.debug(f"Breaking chunk due to punctuation: '{current_chunk_words[-1]}'")
            
            # 4. Too many words (over 6)
            elif len(current_chunk_words) >= 6:
                should_break = True
                logger.debug(f"Breaking chunk due to word count: {len(current_chunk_words)} words")
            
            # 5. Large time gap between words (>0.5s pause)
            elif word_start - current_chunk_end > 0.5:
                should_break = True
                logger.debug(f"Breaking chunk due to speech gap: {word_start - current_chunk_end:.2f}s")
            
            if should_break and current_chunk_words:
                # Finalize current chunk
                chunk_duration = current_chunk_end - current_chunk_start
                
                # Ensure minimum duration for readability
                if chunk_duration < min_duration_s:
                    current_chunk_end = current_chunk_start + min_duration_s
                
                chunk_text = " ".join(current_chunk_words)
                segments.append(SubtitleSegment(
                    start_time=current_chunk_start,
                    end_time=current_chunk_end,
                    text=chunk_text
                ))
                
                logger.debug(f"Speech-sync chunk: '{chunk_text}' ({current_chunk_start:.3f}s - {current_chunk_end:.3f}s)")
                
                # Start new chunk with current word
                current_chunk_start = word_start
                current_chunk_words = [word_text]
                current_chunk_end = word_end
            else:
                # Add word to current chunk
                current_chunk_words.append(word_text)
                current_chunk_end = word_end
        
        # Handle final chunk
        if current_chunk_words and current_chunk_start is not None:
            chunk_duration = current_chunk_end - current_chunk_start
            
            # Ensure minimum duration for readability
            if chunk_duration < min_duration_s:
                current_chunk_end = current_chunk_start + min_duration_s
            
            chunk_text = " ".join(current_chunk_words)
            segments.append(SubtitleSegment(
                start_time=current_chunk_start,
                end_time=current_chunk_end,
                text=chunk_text
            ))
            
            logger.debug(f"Final speech-sync chunk: '{chunk_text}' ({current_chunk_start:.3f}s - {current_chunk_end:.3f}s)")
        
        logger.info(f"🎯 Created {len(segments)} speech-synchronized chunks")
        
        # Post-process to ensure no timing overlaps and add text wrapping
        return self._fix_timing_overlaps_and_wrap_text(segments)
    
    def _fix_timing_overlaps_and_wrap_text(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Fix timing overlaps and add text wrapping to segments.
        
        Args:
            segments: Input segments that may have timing overlaps
            
        Returns:
            Fixed segments with sequential timing and wrapped text
        """
        if not segments:
            return []
        
        logger.debug(f"🔧 Fixing timing overlaps and wrapping text for {len(segments)} segments")
        
        fixed_segments = []
        min_duration_s = self.min_word_duration_ms / 1000.0
        
        for i, segment in enumerate(segments):
            # Handle text wrapping first
            wrapped_text = self._wrap_text_for_subtitle(segment.text)
            
            # Fix timing overlaps
            start_time = segment.start_time
            end_time = segment.end_time
            
            # Check for overlap with previous segment
            if fixed_segments and start_time < fixed_segments[-1].end_time:
                # Overlap detected - adjust start time to be after previous segment
                previous_end = fixed_segments[-1].end_time
                gap_ms = 50  # 50ms gap between subtitles for readability
                start_time = previous_end + (gap_ms / 1000.0)
                
                logger.debug(f"Fixed overlap: moved start from {segment.start_time:.3f}s to {start_time:.3f}s")
            
            # Ensure minimum duration
            duration = end_time - start_time
            if duration < min_duration_s:
                end_time = start_time + min_duration_s
                logger.debug(f"Extended duration from {duration:.3f}s to {min_duration_s:.3f}s")
            
            # Check if this adjustment would overlap with next segment
            if i + 1 < len(segments):
                next_segment = segments[i + 1]
                if end_time > next_segment.start_time:
                    # Would overlap with next - cap at next segment start minus small gap
                    gap_ms = 50
                    max_end_time = next_segment.start_time - (gap_ms / 1000.0)
                    if max_end_time > start_time:
                        end_time = max_end_time
                        logger.debug(f"Capped end time to avoid next overlap: {end_time:.3f}s")
            
            fixed_segments.append(SubtitleSegment(
                start_time=start_time,
                end_time=end_time,
                text=wrapped_text
            ))
        
        logger.info(f"✅ Fixed timing overlaps for {len(fixed_segments)} segments")
        return fixed_segments
    
    def _wrap_text_for_subtitle(self, text: str) -> str:
        """Wrap long text into multiple lines for better readability.
        
        Args:
            text: Input text that may be too long for one line
            
        Returns:
            Text wrapped into multiple lines with newlines
        """
        max_chars_per_line = self.max_chars_per_line
        max_lines = self.max_lines
        
        # If text is short enough, return as-is
        if len(text) <= max_chars_per_line:
            return text
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            # Check if adding this word would exceed line length
            word_length = len(word)
            space_length = 1 if current_line else 0
            total_length = current_length + space_length + word_length
            
            if total_length <= max_chars_per_line or not current_line:
                # Add word to current line
                current_line.append(word)
                current_length = total_length
            else:
                # Start new line
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_length
                
                # Stop if we've reached max lines
                if len(lines) >= max_lines - 1:
                    # Add remaining words to last line
                    remaining_words = words[words.index(word) + 1:]
                    if remaining_words:
                        current_line.extend(remaining_words)
                    break
        
        # Add final line
        if current_line:
            lines.append(" ".join(current_line))
        
        # Limit to max lines
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        
        wrapped_text = "\n".join(lines)
        
        if len(lines) > 1:
            logger.debug(f"Wrapped text: '{text}' -> {len(lines)} lines")
        
        return wrapped_text
    
    def _format_time_srt(self, seconds: float) -> str:
        """Format time for SRT format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string for SRT
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _format_time_vtt(self, seconds: float) -> str:
        """Format time for VTT format (HH:MM:SS.mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string for VTT
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"
    
    def _format_time_simple(self, seconds: float) -> str:
        """Format time in a simple readable format with milliseconds for CapCut mode.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string (MM:SS.mmm for CapCut, MM:SS for traditional)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        if self.capcut_mode:
            # Show milliseconds for CapCut mode
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"
            else:
                return f"{minutes:02d}:{secs:02d}.{millisecs:03d}"
        else:
            # Traditional format without milliseconds
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{secs:02d}"
            else:
                return f"{minutes:02d}:{secs:02d}"
    
    def _groq_segments_to_subtitle_segments(self, groq_segments: List[Any]) -> List[SubtitleSegment]:
        """Convert Groq transcription segments to subtitle segments.
        
        Args:
            groq_segments: Groq transcription segments (can be dicts or objects)
            
        Returns:
            List of subtitle segments
        """
        subtitle_segments = []
        
        for segment in groq_segments:
            # Handle both dictionary and object formats
            if isinstance(segment, dict):
                # Dictionary format: {'text': '...', 'start': 0.0, 'end': 3.5}
                text = segment.get('text', '').strip()
                start_time = segment.get('start', 0.0)
                end_time = segment.get('end', 0.0)
            else:
                # Object format: segment.text, segment.start, segment.end
                text = getattr(segment, 'text', '').strip()
                start_time = getattr(segment, 'start', 0.0)
                end_time = getattr(segment, 'end', 0.0)
            
            if not text:
                continue
            
            subtitle_segments.append(SubtitleSegment(
                start_time=start_time,
                end_time=end_time,
                text=text
            ))
        
        return subtitle_segments
    
    def process_segments(self, groq_segments: List[Any], word_timestamps: List[Any] = None) -> List[SubtitleSegment]:
        """Process Groq segments into optimized subtitle segments.
        
        Args:
            groq_segments: Raw Groq transcription segments
            word_timestamps: Optional word-level timing data for speech sync
            
        Returns:
            Processed subtitle segments
        """
        try:
            # Speech sync mode takes priority if word timestamps are available
            if self.speech_sync_mode and word_timestamps:
                logger.info(f"🎯 Processing {len(word_timestamps)} words in SPEECH SYNC mode")
                return self._create_speech_sync_chunks(word_timestamps)
            
            logger.info(f"Processing {len(groq_segments)} Groq segments")
            
            # Convert to subtitle segments
            subtitle_segments = self._groq_segments_to_subtitle_segments(groq_segments)
            
            # Merge micro-gaps
            merged_segments = self._merge_micro_gaps(subtitle_segments)
            
            # Process segments based on mode
            final_segments = []
            
            if self.capcut_mode:
                # CapCut-style: Create punch word chunks with overlapping timing
                logger.info(f"🎬 Processing in CapCut mode: creating punch-word chunks")
                
                for segment in merged_segments:
                    word_chunks = self._create_capcut_word_chunks(
                        text=segment.text,
                        start_time=segment.start_time,
                        end_time=segment.end_time
                    )
                    final_segments.extend(word_chunks)
                    
                    logger.debug(f"CapCut segment '{segment.text[:30]}...' -> {len(word_chunks)} word chunks")
                
            else:
                # Legacy mode: Traditional text wrapping with splitting
                logger.info(f"📝 Processing in Legacy mode: traditional subtitle wrapping")
                
                for segment in merged_segments:
                    current_text = segment.text
                    current_start = segment.start_time
                    segment_duration = segment.end_time - segment.start_time
                    
                    # Keep processing until all text is handled
                    iteration = 0
                    while current_text.strip():
                        iteration += 1
                        wrapped_lines, remaining_text = self._wrap_text(current_text)
                        
                        if wrapped_lines:
                            # Calculate duration for this sub-segment
                            if remaining_text.strip():
                                # If there's remaining text, this is a partial segment
                                # Estimate duration based on character proportion
                                chars_used = sum(len(line) for line in wrapped_lines)
                                total_chars = len(segment.text)
                                duration_fraction = chars_used / total_chars if total_chars > 0 else 1.0
                                sub_duration = segment_duration * duration_fraction
                                current_end = current_start + sub_duration
                                
                                logger.debug(f"Split segment {iteration}: '{' '.join(wrapped_lines)[:50]}...' + remaining: '{remaining_text[:30]}...'")
                            else:
                                # Last segment gets remaining time
                                current_end = segment.end_time
                            
                            final_segments.append(SubtitleSegment(
                                start_time=current_start,
                                end_time=current_end,
                                text="\n".join(wrapped_lines)
                            ))
                            
                            # Update for next iteration
                            current_text = remaining_text
                            current_start = current_end
                        else:
                            # No lines could be wrapped (shouldn't happen)
                            logger.warning(f"Could not wrap text: '{current_text[:50]}...'")
                            break
                        
                        # Safety check to prevent infinite loops
                        if iteration > 10:
                            logger.warning(f"Text wrapping reached maximum iterations for segment, truncating remaining: '{current_text[:50]}...'")
                            break
            
            logger.info(f"Final processed segments: {len(final_segments)}")
            
            # Print subtitles to console
            self._print_subtitles_to_console(final_segments)
            
            return final_segments
            
        except Exception as e:
            raise SubtitleFormatError(f"Failed to process segments: {str(e)}")
    
    def _print_subtitles_to_console(self, segments: List[SubtitleSegment]) -> None:
        """Print formatted subtitles to console.
        
        Args:
            segments: List of subtitle segments to print
        """
        if not segments:
            print("\n⚠️  No subtitle segments to display\n")
            sys.stdout.flush()
            return
        
        print("\n" + "="*80)
        print(f"📝 GENERATED SUBTITLES ({len(segments)} segments)")
        print("="*80)
        
        for i, segment in enumerate(segments, 1):
            start_time = self._format_time_simple(segment.start_time)
            end_time = self._format_time_simple(segment.end_time)
            duration = segment.end_time - segment.start_time
            
            print(f"\n[{i:3d}] {start_time} --> {end_time} ({duration:.1f}s)")
            
            # Handle multi-line text
            lines = segment.text.split('\n')
            for line in lines:
                print(f"      {line}")
        
        print("\n" + "="*80 + "\n")
        sys.stdout.flush()
    
    def generate_srt(self, segments: List[SubtitleSegment]) -> str:
        """Generate SRT subtitle content.
        
        Args:
            segments: List of subtitle segments
            
        Returns:
            SRT content as string
        """
        try:
            srt_content = []
            
            for i, segment in enumerate(segments, 1):
                start_time = self._format_time_srt(segment.start_time)
                end_time = self._format_time_srt(segment.end_time)
                
                srt_content.extend([
                    str(i),
                    f"{start_time} --> {end_time}",
                    segment.text,
                    ""  # Empty line separator
                ])
            
            return "\n".join(srt_content)
            
        except Exception as e:
            raise SubtitleFormatError(f"Failed to generate SRT: {str(e)}")
    
    def generate_vtt(self, segments: List[SubtitleSegment]) -> str:
        """Generate VTT subtitle content.
        
        Args:
            segments: List of subtitle segments
            
        Returns:
            VTT content as string
        """
        try:
            vtt_content = ["WEBVTT", ""]
            
            for segment in segments:
                start_time = self._format_time_vtt(segment.start_time)
                end_time = self._format_time_vtt(segment.end_time)
                
                vtt_content.extend([
                    f"{start_time} --> {end_time}",
                    segment.text,
                    ""  # Empty line separator
                ])
            
            return "\n".join(vtt_content)
            
        except Exception as e:
            raise SubtitleFormatError(f"Failed to generate VTT: {str(e)}")
    
    def save_subtitles(
        self,
        segments: List[SubtitleSegment],
        output_dir: str,
        filename_base: str
    ) -> Tuple[str, str]:
        """Save subtitle files in both SRT and VTT formats.
        
        Args:
            segments: List of subtitle segments
            output_dir: Output directory path
            filename_base: Base filename without extension
            
        Returns:
            Tuple of (srt_path, vtt_path)
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate content
            srt_content = self.generate_srt(segments)
            vtt_content = self.generate_vtt(segments)
            
            # Save files
            srt_path = output_path / f"{filename_base}.srt"
            vtt_path = output_path / f"{filename_base}.vtt"
            
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)
            
            logger.info(f"Saved subtitles: {srt_path}, {vtt_path}")
            return str(srt_path), str(vtt_path)
            
        except Exception as e:
            raise SubtitleFormatError(f"Failed to save subtitles: {str(e)}")


def convert_groq_to_subtitles(
    groq_segments: List[Any],
    output_dir: str,
    filename_base: str,
    max_chars_per_line: int = 50,  # Legacy parameter
    max_lines: int = 2,  # Legacy parameter
    merge_gap_threshold_ms: int = 200,
    capcut_mode: bool = True,  # Enable CapCut-style punch words by default
    speech_sync_mode: bool = False,  # Enable true speech synchronization
    word_timestamps: List[Any] = None,  # Word-level timing data for speech sync
    min_word_duration_ms: int = 800,  # CapCut: Min display time per word chunk
    max_word_duration_ms: int = 1500,  # CapCut: Max display time per word chunk
    word_overlap_ms: int = 150  # CapCut: Overlap between word chunks
) -> Tuple[str, str]:
    """Convenience function to convert Groq segments to subtitle files.
    
    Args:
        groq_segments: Groq transcription segments
        output_dir: Output directory path
        filename_base: Base filename without extension
        max_chars_per_line: Maximum characters per subtitle line (legacy mode only)
        max_lines: Maximum number of lines per subtitle (legacy mode only)
        merge_gap_threshold_ms: Merge segments with gaps smaller than this (ms)
        capcut_mode: Enable CapCut-style adaptive word chunks
        speech_sync_mode: Enable true speech synchronization using word timestamps
        word_timestamps: Word-level timing data from Groq for speech sync
        min_word_duration_ms: Minimum display time per word chunk
        max_word_duration_ms: Maximum display time per word chunk
        word_overlap_ms: Overlap between word chunks for smooth transitions
        
    Returns:
        Tuple of (srt_path, vtt_path)
    """
    processor = SubtitleProcessor(
        max_chars_per_line=max_chars_per_line,
        max_lines=max_lines,
        merge_gap_threshold_ms=merge_gap_threshold_ms,
        capcut_mode=capcut_mode,
        speech_sync_mode=speech_sync_mode,
        min_word_duration_ms=min_word_duration_ms,
        max_word_duration_ms=max_word_duration_ms,
        word_overlap_ms=word_overlap_ms
    )
    segments = processor.process_segments(groq_segments, word_timestamps)
    return processor.save_subtitles(segments, output_dir, filename_base) 