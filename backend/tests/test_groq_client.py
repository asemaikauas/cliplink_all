"""Unit tests for Groq client wrapper."""

import pytest
from unittest.mock import Mock, patch, mock_open
import os

from app.services.groq_client import GroqClient, transcribe
from app.exceptions import TranscriptionError, VADError


class TestGroqClient:
    """Test GroqClient class."""
    
    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        with patch('groq.Groq') as mock_groq:
            client = GroqClient(api_key="test-key")
            assert client.api_key == "test-key"
            assert client.model == "whisper-large-v3"
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with pytest.raises(TranscriptionError, match="GROQ_API_KEY not found"):
            GroqClient()
    
    @patch('pydub.AudioSegment.from_file')
    @patch('pydub.silence.detect_silence')
    def test_apply_vad_filtering_success(self, mock_detect, mock_from_file):
        """Test successful VAD filtering."""
        mock_audio = Mock()
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio
        mock_detect.return_value = [(1000, 2000)]
        
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        
        with patch('groq.Groq'):
            client = GroqClient(api_key="test-key")
            result = client._apply_vad_filtering("/test/audio.wav")
            assert result == "/test/audio_vad_filtered.wav"
    
    @patch('builtins.open', new_callable=mock_open, read_data=b"audio data")
    @patch('os.path.getsize')
    @patch('os.remove')
    def test_transcribe_success(self, mock_remove, mock_getsize, mock_file):
        """Test successful transcription."""
        mock_groq_client = Mock()
        mock_transcription = Mock()
        mock_transcription.segments = [Mock(start=1.0, end=2.0, text="Hello")]
        mock_transcription.language = "en"
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_transcription
        mock_getsize.return_value = 1024 * 1024
        
        with patch('groq.Groq', return_value=mock_groq_client):
            client = GroqClient(api_key="test-key")
            
            with patch.object(client, '_apply_vad_filtering', return_value="/test/filtered.wav"):
                result = client.transcribe("/test/audio.wav", apply_vad=True)
        
        assert result["segments"] == mock_transcription.segments
        assert result["language"] == "en"
        assert result["cost_usd"] > 0
        assert result["latency_ms"] > 0
    
    def test_transcribe_groq_api_failure(self):
        """Test transcription with Groq API failure."""
        mock_groq_client = Mock()
        mock_groq_client.audio.transcriptions.create.side_effect = Exception("API Error")
        
        with patch('groq.Groq', return_value=mock_groq_client):
            client = GroqClient(api_key="test-key")
            
            with pytest.raises(TranscriptionError, match="Transcription failed"):
                client.transcribe("/test/audio.wav", apply_vad=False)


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    @patch.object(GroqClient, '__init__', return_value=None)
    @patch.object(GroqClient, 'transcribe')
    def test_transcribe_function(self, mock_transcribe_method, mock_init):
        """Test transcribe convenience function."""
        expected_result = {"segments": [], "language": "en", "cost_usd": 0.05, "latency_ms": 1000}
        mock_transcribe_method.return_value = expected_result
        
        result = transcribe("/test/audio.wav", apply_vad=True, task_id="test-123")
        assert result == expected_result 