"""Integration tests for subtitle router."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.exceptions import TranscriptionError, BurnInError


client = TestClient(app)


class TestSubtitleEndpoint:
    """Test subtitle processing endpoint."""
    
    @patch('app.routers.subtitles.transcribe')
    @patch('app.routers.subtitles.convert_groq_to_subtitles')
    @patch('app.routers.subtitles.burn_subtitles_to_video')
    @patch('os.path.exists')
    def test_create_subtitles_success(self, mock_exists, mock_burn, mock_convert, mock_transcribe):
        """Test successful subtitle creation."""
        mock_exists.return_value = True
        
        # Mock transcription
        mock_transcribe.return_value = {
            "segments": [Mock(start=1.0, end=2.0, text="Hello")],
            "language": "en",
            "cost_usd": 0.05,
            "latency_ms": 1000
        }
        
        # Mock subtitle conversion
        mock_convert.return_value = ("/output/video.srt", "/output/video.vtt")
        
        # Mock burn-in
        mock_burn.return_value = "/output/video_subtitled.mp4"
        
        response = client.post(
            "/subtitles",
            json={
                "video_path": "/test/video.mp4",
                "burn_in": True,
                "font_size_pct": 4.5,
                "export_codec": "h264"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["srt_path"] == "/output/video.srt"
        assert data["vtt_path"] == "/output/video.vtt"
        assert data["burned_video_path"] == "/output/video_subtitled.mp4"
        assert data["language"] == "en"
        assert data["cost_usd"] == 0.05
        assert data["latency_ms"] > 0
    
    def test_create_subtitles_video_not_found(self):
        """Test subtitle creation with missing video file."""
        with patch('os.path.exists', return_value=False):
            response = client.post(
                "/subtitles",
                json={"video_path": "/missing/video.mp4"}
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
    
    @patch('app.routers.subtitles.transcribe')
    @patch('os.path.exists')
    def test_create_subtitles_transcription_error(self, mock_exists, mock_transcribe):
        """Test handling of transcription errors."""
        mock_exists.return_value = True
        mock_transcribe.side_effect = TranscriptionError("API failed")
        
        response = client.post(
            "/subtitles",
            json={"video_path": "/test/video.mp4"}
        )
        
        assert response.status_code == 500
        assert "Transcription failed" in response.json()["detail"]
    
    def test_subtitle_request_validation(self):
        """Test request validation."""
        # Missing required field
        response = client.post("/subtitles", json={})
        assert response.status_code == 422
        
        # Invalid font size
        response = client.post(
            "/subtitles",
            json={
                "video_path": "/test/video.mp4",
                "font_size_pct": 15.0  # Too large
            }
        )
        assert response.status_code == 422


class TestHealthCheck:
    """Test health check endpoint."""
    
    @patch('app.routers.subtitles.BurnInRenderer')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_health_check_healthy(self, mock_renderer):
        """Test healthy service response."""
        # Mock successful renderer initialization
        mock_renderer.return_value = Mock()
        
        response = client.get("/subtitles/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["groq_api_available"] is True
        assert data["ffmpeg_available"] is True
    
    @patch('app.routers.subtitles.BurnInRenderer')
    @patch.dict('os.environ', {}, clear=True)
    def test_health_check_missing_groq_key(self, mock_renderer):
        """Test health check with missing Groq API key."""
        mock_renderer.return_value = Mock()
        
        response = client.get("/subtitles/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["groq_api_available"] is False
    
    @patch('app.routers.subtitles.BurnInRenderer')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_health_check_ffmpeg_unavailable(self, mock_renderer):
        """Test health check with FFmpeg unavailable."""
        mock_renderer.side_effect = Exception("FFmpeg not found")
        
        response = client.get("/subtitles/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ffmpeg_available"] is False 