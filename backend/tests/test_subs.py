"""Unit tests for subtitle post-processor."""

import pytest
from unittest.mock import Mock, patch, mock_open
from dataclasses import dataclass
from typing import List

from app.services.subs import (
    SubtitleProcessor, 
    SubtitleSegment, 
    convert_groq_to_subtitles
)
from app.exceptions import SubtitleFormatError


@dataclass
class MockGroqSegment:
    """Mock Groq segment for testing."""
    start: float
    end: float
    text: str


class TestSubtitleSegment:
    """Test SubtitleSegment class."""
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        segment = SubtitleSegment(start_time=1.0, end_time=3.5, text="Hello")
        assert segment.duration() == 2.5


class TestSubtitleProcessor:
    """Test SubtitleProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = SubtitleProcessor(
            max_chars_per_line=20,
            max_lines=2,
            merge_gap_threshold_ms=300
        )
    
    def test_merge_micro_gaps(self):
        """Test merging segments with small gaps."""
        segments = [
            SubtitleSegment(start_time=1.0, end_time=2.0, text="Hello"),
            SubtitleSegment(start_time=2.1, end_time=3.0, text="world"),  # 100ms gap
            SubtitleSegment(start_time=3.5, end_time=4.0, text="again")   # 500ms gap
        ]
        
        merged = self.processor._merge_micro_gaps(segments)
        
        # Should merge first two segments (gap < 300ms) but not the third
        assert len(merged) == 2
        assert merged[0].text == "Hello world"
        assert merged[0].start_time == 1.0
        assert merged[0].end_time == 3.0
        assert merged[1].text == "again"
    
    def test_merge_micro_gaps_empty_list(self):
        """Test merging with empty segment list."""
        merged = self.processor._merge_micro_gaps([])
        assert merged == []
    
    def test_wrap_text_single_line(self):
        """Test text wrapping for single line."""
        text = "Short text"
        wrapped = self.processor._wrap_text(text)
        assert wrapped == ["Short text"]
    
    def test_wrap_text_multiple_lines(self):
        """Test text wrapping for multiple lines."""
        text = "This is a very long text that should be wrapped across multiple lines"
        wrapped = self.processor._wrap_text(text)
        
        assert len(wrapped) <= 2  # Max lines
        for line in wrapped:
            assert len(line) <= 20  # Max chars per line
    
    def test_wrap_text_max_lines_exceeded(self):
        """Test text wrapping when max lines is exceeded."""
        text = "Word " * 20  # Long text that would need many lines
        wrapped = self.processor._wrap_text(text)
        
        assert len(wrapped) <= 2  # Should not exceed max lines
    
    def test_format_time_srt(self):
        """Test SRT time formatting."""
        time_str = self.processor._format_time_srt(3661.123)
        assert time_str == "01:01:01,123"
    
    def test_format_time_vtt(self):
        """Test VTT time formatting."""
        time_str = self.processor._format_time_vtt(3661.123)
        assert time_str == "01:01:01.123"
    
    def test_groq_segments_to_subtitle_segments(self):
        """Test conversion from Groq segments."""
        groq_segments = [
            MockGroqSegment(start=1.0, end=2.0, text="Hello"),
            MockGroqSegment(start=2.5, end=3.5, text="  world  "),  # With whitespace
            MockGroqSegment(start=4.0, end=4.5, text=""),  # Empty text
        ]
        
        subtitle_segments = self.processor._groq_segments_to_subtitle_segments(groq_segments)
        
        # Should filter out empty segments and strip whitespace
        assert len(subtitle_segments) == 2
        assert subtitle_segments[0].text == "Hello"
        assert subtitle_segments[1].text == "world"
    
    def test_process_segments_full_pipeline(self):
        """Test complete segment processing pipeline."""
        groq_segments = [
            MockGroqSegment(start=1.0, end=2.0, text="Hello"),
            MockGroqSegment(start=2.1, end=3.0, text="world"),  # Will be merged
            MockGroqSegment(start=4.0, end=5.0, text="This is a very long sentence that needs wrapping"),
        ]
        
        processed = self.processor.process_segments(groq_segments)
        
        # Should have merged first two and wrapped the third
        assert len(processed) >= 2
        assert "Hello world" in processed[0].text
    
    def test_generate_srt(self):
        """Test SRT content generation."""
        segments = [
            SubtitleSegment(start_time=1.0, end_time=2.0, text="Hello"),
            SubtitleSegment(start_time=3.0, end_time=4.0, text="World\nMultiline"),
        ]
        
        srt_content = self.processor.generate_srt(segments)
        
        expected_lines = [
            "1",
            "00:00:01,000 --> 00:00:02,000",
            "Hello",
            "",
            "2",
            "00:00:03,000 --> 00:00:04,000",
            "World\nMultiline",
            ""
        ]
        
        assert srt_content == "\n".join(expected_lines)
    
    def test_generate_vtt(self):
        """Test VTT content generation."""
        segments = [
            SubtitleSegment(start_time=1.0, end_time=2.0, text="Hello"),
            SubtitleSegment(start_time=3.0, end_time=4.0, text="World"),
        ]
        
        vtt_content = self.processor.generate_vtt(segments)
        
        assert vtt_content.startswith("WEBVTT\n")
        assert "00:00:01.000 --> 00:00:02.000" in vtt_content
        assert "Hello" in vtt_content
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_save_subtitles(self, mock_mkdir, mock_file):
        """Test saving subtitle files."""
        segments = [
            SubtitleSegment(start_time=1.0, end_time=2.0, text="Hello"),
        ]
        
        srt_path, vtt_path = self.processor.save_subtitles(
            segments, "/test/output", "video"
        )
        
        assert srt_path == "/test/output/video.srt"
        assert vtt_path == "/test/output/video.vtt"
        
        # Verify files were written
        assert mock_file.call_count == 2  # SRT and VTT files
    
    def test_generate_srt_error_handling(self):
        """Test SRT generation error handling."""
        # Create a segment that will cause an error
        segments = [SubtitleSegment(start_time="invalid", end_time=2.0, text="Hello")]
        
        with pytest.raises(SubtitleFormatError):
            self.processor.generate_srt(segments)


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch("app.services.subs.SubtitleProcessor")
    def test_convert_groq_to_subtitles(self, mock_processor_class):
        """Test convert_groq_to_subtitles convenience function."""
        # Mock the processor
        mock_processor = Mock()
        mock_processor.process_segments.return_value = [
            SubtitleSegment(start_time=1.0, end_time=2.0, text="Hello")
        ]
        mock_processor.save_subtitles.return_value = ("/test.srt", "/test.vtt")
        mock_processor_class.return_value = mock_processor
        
        groq_segments = [MockGroqSegment(start=1.0, end=2.0, text="Hello")]
        
        srt_path, vtt_path = convert_groq_to_subtitles(
            groq_segments, "/output", "video", max_chars_per_line=30
        )
        
        assert srt_path == "/test.srt"
        assert vtt_path == "/test.vtt"
        
        # Verify processor was configured correctly
        mock_processor_class.assert_called_once_with(30, 2, 200)
        mock_processor.process_segments.assert_called_once_with(groq_segments)
        mock_processor.save_subtitles.assert_called_once_with(
            mock_processor.process_segments.return_value, "/output", "video"
        )


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_segments_list(self):
        """Test processing empty segments list."""
        processor = SubtitleProcessor()
        
        # Should not raise error and return empty results
        processed = processor.process_segments([])
        assert processed == []
        
        srt_content = processor.generate_srt([])
        assert srt_content == ""
        
        vtt_content = processor.generate_vtt([])
        assert vtt_content == "WEBVTT\n"
    
    def test_segments_with_zero_duration(self):
        """Test segments with zero or negative duration."""
        segments = [
            SubtitleSegment(start_time=2.0, end_time=2.0, text="Zero duration"),
            SubtitleSegment(start_time=3.0, end_time=2.5, text="Negative duration"),
        ]
        
        processor = SubtitleProcessor()
        
        # Should handle gracefully
        srt_content = processor.generate_srt(segments)
        assert "Zero duration" in srt_content
        assert "Negative duration" in srt_content
    
    def test_unicode_text_handling(self):
        """Test handling of unicode text."""
        segments = [
            SubtitleSegment(start_time=1.0, end_time=2.0, text="Hello 世界 🌍"),
        ]
        
        processor = SubtitleProcessor()
        
        srt_content = processor.generate_srt(segments)
        vtt_content = processor.generate_vtt(segments)
        
        assert "Hello 世界 🌍" in srt_content
        assert "Hello 世界 🌍" in vtt_content
    
    def test_very_long_single_word(self):
        """Test handling of very long single words."""
        long_word = "a" * 100
        processor = SubtitleProcessor(max_chars_per_line=20)
        
        wrapped = processor._wrap_text(long_word)
        
        # Should include the long word even if it exceeds line length
        assert len(wrapped) == 1
        assert wrapped[0] == long_word 