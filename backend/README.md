# ClipLink Subtitle Subsystem

[![Coverage Status](https://img.shields.io/badge/coverage-80%25+-green.svg)](coverage)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Groq](https://img.shields.io/badge/Groq-Whisper%20large--v3-orange.svg)](https://groq.com/)

A high-performance subtitle generation system that integrates with your video processing pipeline. Uses Groq's Whisper large-v3 for ultra-fast, accurate transcription and produces stylish burned-in subtitles optimized for social media platforms.

## Features

### 🎯 Core Functionality
- **Ultra-fast transcription** using Groq Whisper large-v3
- **Dual subtitle formats**: SRT and VTT generation
- **Professional burn-in** with Inter SemiBold styling
- **VAD pre-filtering** removes silent segments (< -45dB for >3s)
- **Smart text processing** with micro-gap merging and word wrapping

### 🎨 Styling
- **Inter SemiBold** font for modern, readable text
- **Dynamic font sizing** (4.5% of video height by default)
- **Professional colors**: White text with semi-transparent black background
- **Social media ready**: Optimized for TikTok, YouTube Shorts, Instagram Reels

### ⚡ Performance
- **VAD optimization** skips silence for faster processing
- **Cost tracking** with real-time USD estimates
- **Structured logging** with task IDs and stage timing
- **Error handling** with custom exception hierarchy

## Quick Start

### Prerequisites

1. **Install FFmpeg**:
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Groq API key**:
   ```bash
   export GROQ_API_KEY="your-groq-api-key-here"
   ```

### Basic Usage

```python
from app.services.groq_client import transcribe
from app.services.subs import convert_groq_to_subtitles
from app.services.burn_in import burn_subtitles_to_video

# 1. Transcribe video
result = transcribe("/path/to/video.mp4", apply_vad=True)

# 2. Generate subtitle files
srt_path, vtt_path = convert_groq_to_subtitles(
    result["segments"], 
    "/output/dir", 
    "video_name"
)

# 3. Burn subtitles into video
burned_video = burn_subtitles_to_video(
    "/path/to/video.mp4",
    srt_path,
    "/output/video_with_subs.mp4"
)
```

### REST API

Start the server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Create subtitles via API:
```bash
curl -X POST "http://localhost:8000/subtitles" \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/path/to/video.mp4",
    "burn_in": true,
    "font_size": 16,
    "export_codec": "h264"
  }'
```

Response:
```json
{
  "srt_path": "/path/to/video.srt",
  "vtt_path": "/path/to/video.vtt", 
  "burned_video_path": "/path/to/video_subtitled.mp4",
  "language": "en",
  "cost_usd": 0.0234,
  "latency_ms": 1247
}
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Input Video   │───▶│  Groq Whisper    │───▶│  Subtitle       │
│   (MP4/H.264)   │    │  Transcription   │    │  Generation     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  VAD Filtering   │    │  SRT/VTT Files  │
                       │  (Silence Removal)│    │  + Burn-in      │
                       └──────────────────┘    └─────────────────┘
```

### Components

- **`groq_client.py`**: Groq Whisper API wrapper with VAD pre-filtering
- **`subs.py`**: Subtitle post-processor (SRT/VTT generation, text optimization)
- **`burn_in.py`**: FFmpeg-based subtitle burn-in renderer
- **`routers/subtitles.py`**: FastAPI endpoint for subtitle processing
- **`exceptions.py`**: Custom exception hierarchy

## Configuration

### Default Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `font_size` | 16 | Font size in pixels |
| `max_chars_per_line` | 42 | Maximum characters per subtitle line |
| `max_lines` | 2 | Maximum lines per subtitle |
| `merge_gap_threshold_ms` | 200 | Merge segments with gaps < 200ms |
| `vad_silence_threshold` | -45 | Silence threshold in dB |
| `vad_min_duration` | 3000 | Min silence duration to remove (ms) |

### Styling Template

The burn-in renderer uses this ASS styling template:

```
Fontname=Inter SemiBold
Fontsize=h*0.045  (4.5% of video height)
PrimaryColour=&Hffffff&  (White text)
BackColour=&H66000000&   (Semi-transparent black background)
Alignment=2              (Bottom center)
MarginV=40              (40px bottom margin)
```

## Testing

Run the test suite with coverage:

```bash
# Run tests with coverage
pytest --cov=app --cov-report=term-missing --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests
```

### Test Coverage

The test suite targets 80%+ coverage and includes:

- **Unit tests** for subtitle generation edge cases
- **Integration tests** for API endpoints
- **FFmpeg command assembly** validation
- **Error handling** scenarios
- **Unicode text** handling
- **VAD filtering** edge cases

## Error Handling

The system uses a hierarchical exception system:

```python
SubtitleError                    # Base exception
├── TranscriptionError          # Groq API failures
├── SubtitleFormatError         # SRT/VTT generation issues
├── BurnInError                 # FFmpeg processing failures
└── VADError                    # Voice activity detection issues
```

## Performance Optimization

### VAD Pre-filtering
- Removes silent segments before uploading to Groq
- Reduces transcription time and costs
- Configurable silence threshold and duration

### Cost Management
- Real-time cost estimation based on audio duration
- Detailed logging of processing costs
- Groq pricing: ~$0.111 per hour of audio

### Caching & Cleanup
- Automatic cleanup of temporary VAD-filtered files
- Graceful handling of cleanup failures
- Structured logging for debugging

## Deployment

### Environment Variables

```bash
GROQ_API_KEY=your-groq-api-key-here
```

### Health Checks

The system provides health check endpoints:

```bash
# Overall API health
curl http://localhost:8000/health

# Subtitle service health
curl http://localhost:8000/subtitles/health
```

### Monitoring

Structured logs include:
- `task_id`: Unique identifier for each request
- `stage`: Processing stage (transcription, generation, burn-in)
- `elapsed_ms`: Stage timing for performance monitoring

## License

MIT License - see LICENSE file for details.

## Contributing

1. Follow the existing code style (typed, black-formatted)
2. Add tests for new functionality
3. Maintain 80%+ test coverage
4. Update documentation for API changes 