# ClipLink API - Complete Workflow

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Environment Variables
Create `.env` file in backend directory:
```bash
YOUTUBE_TRANSCRIPT_API=your_youtube_transcript_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Start Server
```bash
uvicorn app.main:app --reload
```

Server will be available at: http://localhost:8000

## 📋 API Endpoints

### Complete Workflow
**POST** `/workflow/process-complete`
```json
{
  "youtube_url": "https://youtube.com/watch?v=..."
}
```

**Flow:**
1. 📝 Extract transcript from YouTube
2. 🤖 Analyze with Gemini AI 
3. 📥 Download video
4. ✂️ Cut into viral clips

**Response:**
- Video info (title, category, etc.)
- Gemini analysis results
- Created clip file paths

### Analysis Only
**POST** `/workflow/analyze-only`
```json
{
  "youtube_url": "https://youtube.com/watch?v=..."
}
```

**Flow:**
1. 📝 Extract transcript 
2. 🤖 Analyze with Gemini AI
(No download/cutting)

### Individual Endpoints
- **POST** `/transcript` - Extract transcript only
- **POST** `/analyze` - Extract + analyze only

## 🧪 Testing

### Test Complete Workflow
```bash
python test_workflow_api.py
```

### Test Individual Functions
```bash
python test_youtube_extended.py
```

### Test MoviePy 2.2.1 API
```bash
python moviepy_v2_example.py
```

## 📁 File Structure

After running workflow:
```
backend/
├── downloads/          # Downloaded source videos
├── clips/             # Generated viral clips
├── app/
│   ├── services/
│   │   ├── youtube.py     # Video download & cutting (MoviePy 2.2.1)
│   │   ├── transcript.py  # Transcript extraction  
│   │   └── gemini.py     # AI analysis
│   └── routers/
│       ├── transcript.py  # Basic endpoints
│       └── workflow.py   # Complete workflow
```

## 🎬 MoviePy 2.2.1 Updates

This project uses **MoviePy 2.2.1** with the new API. Key changes from v1.0.3:

| Feature | Old API (v1.0.3) | New API (v2.2.1) |
|---------|------------------|-------------------|
| Import | `from moviepy.editor import VideoFileClip` | `from moviepy import VideoFileClip` |
| Subclip | `.subclip(10, 20)` | `.subclipped(10, 20)` |
| Duration | `.set_duration(10)` | `.with_duration(10)` |
| Position | `.set_position('center')` | `.with_position('center')` |
| Volume | `.volumex(0.8)` | `.with_volume_scaled(0.8)` |
| Export | `verbose=False` | `logger=None` |

> **Reference:** [MoviePy 2.2.1 on PyPI](https://pypi.org/project/moviepy/)

## 📊 Example Usage

```bash
# Start server
uvicorn app.main:app --reload

# Test with curl
curl -X POST "http://localhost:8000/workflow/process-complete" \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://youtube.com/watch?v=YOUR_VIDEO_ID"}'
```

## ⚠️ Notes

- Full workflow can take 5-15 minutes depending on video length
- Requires valid API keys for YouTube Transcript and Gemini
- Downloads are saved in `downloads/` directory
- Clips are saved in `clips/` directory with format: `{index:02d}_{title}.mp4`
- **Updated to MoviePy 2.2.1** with breaking API changes
- Font files may need adjustment for TextClip functionality 