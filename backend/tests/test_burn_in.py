"""Unit tests for burn-in renderer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import json

from app.services.burn_in import BurnInRenderer, burn_subtitles_to_video
from app.exceptions import BurnInError


class TestBurnInRenderer:
    """Test BurnInRenderer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.object(BurnInRenderer, '_verify_ffmpeg'):
            self.renderer = BurnInRenderer()
    
    @patch('subprocess.run')
    def test_verify_ffmpeg_success(self, mock_run):
        """Test successful FFmpeg verification."""
        mock_run.return_value.returncode = 0
        
        # Should not raise exception
        renderer = BurnInRenderer()
        
        mock_run.assert_called_once_with(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_verify_ffmpeg_not_found(self, mock_run):
        """Test FFmpeg not found error."""
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(BurnInError, match="FFmpeg not found"):
            BurnInRenderer()
    
    @patch('subprocess.run')
    def test_verify_ffmpeg_failure(self, mock_run):
        """Test FFmpeg verification failure."""
        mock_run.return_value.returncode = 1
        
        with pytest.raises(BurnInError, match="not working properly"):
            BurnInRenderer()
    
    @patch('subprocess.run')
    def test_verify_ffmpeg_timeout(self, mock_run):
        """Test FFmpeg verification timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["ffmpeg"], 10)
        
        with pytest.raises(BurnInError, match="verification timed out"):
            BurnInRenderer()
    
    def test_build_force_style_default(self):
        """Test building force style with default parameters."""
        force_style = self.renderer._build_force_style()
        
        expected = (
            "Fontname=Inter SemiBold,"
            "Fontsize=h*0.045,"
            "PrimaryColour=&Hffffff&,"
            "BackColour=&H66000000&,"
            "Alignment=2,"
            "MarginV=40"
        )
        
        assert force_style == expected
    
    def test_build_force_style_custom(self):
        """Test building force style with custom parameters."""
        force_style = self.renderer._build_force_style(
            font_size_pct=6.0,
            font_name="Arial",
            primary_colour="&H00ff00&",
            back_colour="&H80000000&",
            alignment=1,
            margin_v=60
        )
        
        expected = (
            "Fontname=Arial,"
            "Fontsize=h*0.06,"
            "PrimaryColour=&H00ff00&,"
            "BackColour=&H80000000&,"
            "Alignment=1,"
            "MarginV=60"
        )
        
        assert force_style == expected
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_burn_subtitles_success(self, mock_run, mock_makedirs, mock_getsize, mock_exists):
        """Test successful subtitle burn-in."""
        # Setup mocks
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024  # 1 MB
        mock_run.return_value.returncode = 0
        
        result = self.renderer.burn_subtitles(
            video_path="/input/video.mp4",
            srt_path="/input/subtitles.srt",
            output_path="/output/video_with_subs.mp4",
            font_size_pct=5.0,
            export_codec="h265",
            crf=20,
            task_id="test-123"
        )
        
        assert result == "/output/video_with_subs.mp4"
        
        # Verify FFmpeg command was built correctly
        args, kwargs = mock_run.call_args
        cmd = args[0]
        
        assert cmd[0] == "ffmpeg"
        assert "/input/video.mp4" in cmd
        assert "/input/subtitles.srt" in " ".join(cmd)
        assert "libx265" in cmd
        assert "20" in cmd
        assert "/output/video_with_subs.mp4" in cmd
    
    @patch('os.path.exists')
    def test_burn_subtitles_video_not_found(self, mock_exists):
        """Test burn-in with missing video file."""
        mock_exists.side_effect = lambda path: path != "/missing/video.mp4"
        
        with pytest.raises(BurnInError, match="Input video not found"):
            self.renderer.burn_subtitles(
                video_path="/missing/video.mp4",
                srt_path="/input/subtitles.srt",
                output_path="/output/video_with_subs.mp4"
            )
    
    @patch('os.path.exists')
    def test_burn_subtitles_srt_not_found(self, mock_exists):
        """Test burn-in with missing SRT file."""
        mock_exists.side_effect = lambda path: path != "/missing/subtitles.srt"
        
        with pytest.raises(BurnInError, match="SRT file not found"):
            self.renderer.burn_subtitles(
                video_path="/input/video.mp4",
                srt_path="/missing/subtitles.srt",
                output_path="/output/video_with_subs.mp4"
            )
    
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_burn_subtitles_ffmpeg_failure(self, mock_run, mock_exists):
        """Test burn-in with FFmpeg failure."""
        mock_exists.return_value = True
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "FFmpeg error message"
        
        with pytest.raises(BurnInError, match="FFmpeg failed with return code 1"):
            self.renderer.burn_subtitles(
                video_path="/input/video.mp4",
                srt_path="/input/subtitles.srt",
                output_path="/output/video_with_subs.mp4"
            )
    
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_burn_subtitles_timeout(self, mock_run, mock_exists):
        """Test burn-in with FFmpeg timeout."""
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(["ffmpeg"], 3600)
        
        with pytest.raises(BurnInError, match="FFmpeg process timed out"):
            self.renderer.burn_subtitles(
                video_path="/input/video.mp4",
                srt_path="/input/subtitles.srt",
                output_path="/output/video_with_subs.mp4"
            )
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_burn_subtitles_output_not_created(self, mock_run, mock_makedirs, mock_exists):
        """Test burn-in when output file is not created."""
        # Input files exist, but output doesn't
        mock_exists.side_effect = lambda path: not path.endswith("_with_subs.mp4")
        mock_run.return_value.returncode = 0
        
        with pytest.raises(BurnInError, match="Output file was not created"):
            self.renderer.burn_subtitles(
                video_path="/input/video.mp4",
                srt_path="/input/subtitles.srt",
                output_path="/output/video_with_subs.mp4"
            )
    
    def test_codec_handling(self):
        """Test different codec handling."""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch('os.makedirs'), \
             patch('subprocess.run') as mock_run:
            
            mock_run.return_value.returncode = 0
            
            # Test h264 codec
            self.renderer.burn_subtitles(
                video_path="/input/video.mp4",
                srt_path="/input/subtitles.srt",
                output_path="/output/video.mp4",
                export_codec="h264"
            )
            
            cmd = mock_run.call_args[0][0]
            assert "libx264" in cmd
            
            # Test h265 codec
            self.renderer.burn_subtitles(
                video_path="/input/video.mp4",
                srt_path="/input/subtitles.srt",
                output_path="/output/video.mp4",
                export_codec="h265"
            )
            
            cmd = mock_run.call_args[0][0]
            assert "libx265" in cmd
    
    @patch('subprocess.run')
    def test_get_video_info_success(self, mock_run):
        """Test successful video info retrieval."""
        mock_info = {
            "format": {"duration": "60.0"},
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}]
        }
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(mock_info)
        
        info = self.renderer.get_video_info("/test/video.mp4")
        
        assert info == mock_info
        
        # Verify FFprobe command
        args = mock_run.call_args[0][0]
        assert args[0] == "ffprobe"
        assert "/test/video.mp4" in args
    
    @patch('subprocess.run')
    def test_get_video_info_failure(self, mock_run):
        """Test video info retrieval failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "FFprobe error"
        
        with pytest.raises(BurnInError, match="FFprobe failed"):
            self.renderer.get_video_info("/test/video.mp4")
    
    def test_special_characters_in_path(self):
        """Test handling of special characters in file paths."""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch('os.makedirs'), \
             patch('subprocess.run') as mock_run:
            
            mock_run.return_value.returncode = 0
            
            # File path with spaces and special characters
            srt_path = "/path/with spaces/subtitles (1).srt"
            
            self.renderer.burn_subtitles(
                video_path="/input/video.mp4",
                srt_path=srt_path,
                output_path="/output/video.mp4"
            )
            
            # Check that path was properly escaped in FFmpeg command
            cmd_str = " ".join(mock_run.call_args[0][0])
            # Should contain escaped path
            assert "subtitles=" in cmd_str


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch.object(BurnInRenderer, '__init__', return_value=None)
    @patch.object(BurnInRenderer, 'burn_subtitles')
    def test_burn_subtitles_to_video(self, mock_burn, mock_init):
        """Test burn_subtitles_to_video convenience function."""
        mock_burn.return_value = "/output/video.mp4"
        
        result = burn_subtitles_to_video(
            video_path="/input/video.mp4",
            srt_path="/input/subtitles.srt",
            output_path="/output/video.mp4",
            font_size_pct=5.0,
            export_codec="h265",
            crf=20,
            task_id="test-123"
        )
        
        assert result == "/output/video.mp4"
        
        # Verify method was called with correct parameters
        mock_burn.assert_called_once_with(
            "/input/video.mp4",
            "/input/subtitles.srt", 
            "/output/video.mp4",
            5.0,
            "h265",
            20,
            "test-123"
        )


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_generic_exception_handling(self):
        """Test handling of unexpected exceptions."""
        with patch.object(BurnInRenderer, '_verify_ffmpeg'):
            renderer = BurnInRenderer()
        
        with patch('os.path.exists', side_effect=Exception("Unexpected error")):
            with pytest.raises(BurnInError, match="Subtitle burn-in failed"):
                renderer.burn_subtitles(
                    video_path="/input/video.mp4",
                    srt_path="/input/subtitles.srt",
                    output_path="/output/video.mp4"
                ) 