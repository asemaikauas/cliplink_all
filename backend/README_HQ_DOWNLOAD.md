# 🎥 High-Quality Video Download Documentation

## 📋 Overview

ClipLink теперь поддерживает скачивание видео в ультра высоком качестве, включая **8K разрешение**!

## 🆕 New Features

### ✨ Supported Quality Options
- **8k** - 8K/4320p (если доступно)
- **4k** - 4K/2160p 
- **1440p** - 2K/QHD
- **1080p** - Full HD
- **720p** - HD
- **best** - Максимальное доступное качество (автоматический выбор)

### 🛠️ New API Endpoints

#### 1. Get Video Information
```http
POST /workflow/video-info
Content-Type: application/json

{
  "youtube_url": "https://youtu.be/VIDEO_ID"
}
```

**Response:**
```json
{
  "success": true,
  "video_info": {
    "id": "VIDEO_ID",
    "title": "Video Title",
    "duration": 1234,
    "view_count": 1000000,
    "uploader": "Channel Name",
    "description": "Video description..."
  },
  "available_formats": [
    {
      "format_id": "571",
      "resolution": "7680x4320",
      "height": 4320,
      "fps": 30,
      "filesize": 2147483648,
      "format_note": "8K"
    }
  ],
  "supported_qualities": ["best", "8k", "4k", "1440p", "1080p", "720p"]
}
```

#### 2. Download Only (New)
```http
POST /workflow/download-only
Content-Type: application/json

{
  "youtube_url": "https://youtu.be/VIDEO_ID",
  "quality": "8k"
}
```

**Response:**
```json
{
  "success": true,
  "video_info": { /* video info */ },
  "download_info": {
    "quality_requested": "8k",
    "file_size_mb": 1024.5,
    "file_path": "/path/to/8K-video.mp4"
  }
}
```

#### 3. Complete Workflow (Updated)
```http
POST /workflow/process-complete
Content-Type: application/json

{
  "youtube_url": "https://youtu.be/VIDEO_ID",
  "quality": "4k"
}
```

**Response:**
```json
{
  "success": true,
  "workflow_steps": {
    "video_info_extraction": true,
    "transcript_extraction": true,
    "gemini_analysis": true,
    "video_download": true,
    "clip_cutting": true
  },
  "video_info": { /* detailed video info */ },
  "download_info": {
    "quality_requested": "4k",
    "file_size_mb": 512.3,
    "file_path": "/path/to/4k-video.mp4"
  },
  "analysis_results": { /* gemini analysis */ },
  "files_created": { /* created clips */ }
}
```

## 🔧 Technical Details

### Quality Selection Logic

```python
# Format selectors for different qualities
format_selectors = {
    "8k": "bestvideo[height>=4320]+bestaudio[ext=m4a]/...",
    "4k": "bestvideo[height<=2160]+bestaudio[ext=m4a]/...",
    "1440p": "bestvideo[height<=1440]+bestaudio[ext=m4a]/...",
    "1080p": "bestvideo[height<=1080]+bestaudio[ext=m4a]/...",
    "720p": "bestvideo[height<=720]+bestaudio[ext=m4a]/...",
    "best": "bestvideo[height>=2160]+bestaudio[ext=m4a]/..."
}
```

### File Naming Convention
- **8K videos**: `8K-{title}-{video_id}.mp4`
- **4K videos**: `4k-{title}-{video_id}.mp4`
- **1440p videos**: `1440p-{title}-{video_id}.mp4`
- **1080p videos**: `1080p-{title}-{video_id}.mp4`
- **720p videos**: `720p-{title}-{video_id}.mp4`
- **Best quality**: `UHQ-{title}-{video_id}.mp4`

### Enhanced yt-dlp Configuration

```python
base_ydl_opts = {
    'merge_output_format': 'mp4',
    'prefer_ffmpeg': True,
    'audioformat': 'best',
    'audioquality': '0',  # Best audio quality
    'http_chunk_size': 10485760,  # 10MB chunks for large files
    'retries': 10,
    'fragment_retries': 10,
}
```

## 🧪 Testing

Run the test script to verify functionality:

```bash
cd backend
python test_hq_download.py
```

### Test Cases
1. **Video Info** - Get detailed video information
2. **Download 1080p** - Download in Full HD
3. **Download 4K** - Download in 4K (optional)
4. **Complete Workflow** - Full pipeline with quality selection

## 📁 File Structure

```
backend/
├── downloads/           # Downloaded videos
│   ├── 8K-*.mp4        # 8K videos
│   ├── 4k-*.mp4        # 4K videos
│   ├── 1440p-*.mp4     # 2K videos
│   ├── 1080p-*.mp4     # Full HD videos
│   └── UHQ-*.mp4       # Best quality videos
├── clips/              # Generated clips
└── app/services/
    └── youtube.py      # Enhanced YouTube service
```

## ⚠️ Important Notes

### File Sizes
- **8K videos**: 500MB - 5GB+ (depending on length)
- **4K videos**: 100MB - 2GB
- **1080p videos**: 50MB - 500MB
- **720p videos**: 20MB - 200MB

### Performance Considerations
1. **8K downloads** require stable internet (100+ Mbps recommended)
2. **Large files** may take significant time to process
3. **Disk space** requirements increase dramatically with higher quality
4. **MoviePy processing** of large files requires more RAM

### Compatibility
- **8K support** depends on YouTube having 8K versions available
- **Format availability** varies by video
- **Fallback mechanism** ensures download success even if preferred quality unavailable

## 🚀 Usage Examples

### Python Usage
```python
from app.services.youtube import youtube_service

# Download 8K video
video_path = youtube_service.download_video(url, "8k")

# Get video information
info = youtube_service.get_video_info(url)

# Get available formats
formats = youtube_service.get_available_formats(url)
```

### cURL Examples
```bash
# Get video info
curl -X POST "http://localhost:8000/workflow/video-info" \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://youtu.be/VIDEO_ID"}'

# Download 4K video
curl -X POST "http://localhost:8000/workflow/download-only" \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://youtu.be/VIDEO_ID", "quality": "4k"}'
```

## 🔄 Backward Compatibility

Все существующие API endpoints продолжают работать:
- Если `quality` не указано, используется `"best"`
- Старые функции (`download_video()` без quality) работают как раньше
- Существующие скрипты не требуют изменений

## 📊 Quality Comparison

| Quality | Resolution | Typical Size | Use Case |
|---------|------------|--------------|----------|
| 8K | 7680×4320 | 1-5GB | Professional editing |
| 4K | 3840×2160 | 200MB-2GB | High-quality content |
| 1440p | 2560×1440 | 100-800MB | Gaming, tech content |
| 1080p | 1920×1080 | 50-500MB | Standard high quality |
| 720p | 1280×720 | 20-200MB | Mobile-friendly |
| best | Variable | Variable | Auto-selection |

## 🎯 Next Steps

1. Test with your favorite YouTube videos
2. Experiment with different quality settings
3. Monitor file sizes and download times
4. Report any issues or suggestions

Happy downloading! 🚀 