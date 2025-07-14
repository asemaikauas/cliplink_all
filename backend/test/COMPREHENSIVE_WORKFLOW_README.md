# 🚀 Comprehensive Workflow Endpoint

The **ultimate all-in-one endpoint** that takes a YouTube URL and produces ready-to-upload vertical clips with burned-in subtitles!

## Complete All-in-One Workflow

This endpoint handles everything in sequence:

1. **Extract transcript** from YouTube using the YouTube Transcript API
2. **Analyze with Gemini AI** to identify viral segments  
3. **Download video** in your specified quality
4. **Generate subtitles** from the audio using Groq Whisper
5. **Cut segments** with optimized vertical cropping and speaker detection
6. **Burn subtitles** directly into each final clip using FFmpeg

The result: Ready-to-upload clips with perfectly timed, styled subtitles!

## Why This Approach?

After analyzing the workflow, we discovered the most efficient approach is:

### ✅ Optimized Vertical Cropping Process
- Downloads full horizontal video
- **Directly processes each segment** to vertical format
- Uses temporary files that are **immediately deleted**
- **No double processing** - single encoding step preserves quality
- **Speaker detection per segment** for optimal cropping

See [VERTICAL_CROP_EXPLANATION.md](./VERTICAL_CROP_EXPLANATION.md) for technical details.

## API Endpoint

```
POST /workflow/process-comprehensive-async
```

## Request Body

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "quality": "1080p",              // best, 8k, 4k, 1440p, 1080p, 720p
  "create_vertical": true,         // Create vertical 9:16 clips
  "smoothing_strength": "very_high", // Motion smoothing: low, medium, high, very_high
  "burn_subtitles": true,          // Burn subtitles into clips
  "font_size": 16,                 // Subtitle font size (12-120)
  "export_codec": "h264",          // Video codec: h264, h265
  "subtitle_style": "capcut"       // Subtitle style: traditional, capcut, speech_sync
}
```

**Note**: The `burn_subtitles`, `font_size`, `export_codec`, and `subtitle_style` parameters are available in the request model but subtitle burning is handled separately for better modularity.

## Example Usage

```bash
curl -X POST "http://localhost:8000/workflow/process-comprehensive-async" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "quality": "1080p",
    "create_vertical": true,
    "burn_subtitles": true,
    "font_size": 16,
    "subtitle_style": "capcut"
  }'
```

## Example Response

```json
{
  "success": true,
  "task_id": "comprehensive_ab12cd34",
  "message": "🎬 Comprehensive workflow started!",
  "workflow_steps": [
    "1. Video info extraction",
    "2. Transcript extraction", 
    "3. Gemini AI analysis",
    "4. Video download",
    "5. Optimized vertical clip cutting"
  ],
  "estimated_time": "10-30 minutes depending on video length and quality"
}
```

## Final Results

When completed:

```json
{
  "status": "completed",
  "result": {
    "workflow_type": "comprehensive",
    "workflow_steps": {
      "video_info_extraction": true,
      "transcript_extraction": true,
      "gemini_analysis": true, 
      "video_download": true,
      "subtitle_generation": true,
      "clip_cutting": true,
      "subtitle_burning": true
    },
    "analysis_results": {
      "viral_segments_found": 5,
      "segments": [...]
    },
    "subtitle_info": {
      "subtitle_style": "capcut",
      "language": "en",
      "subtitle_segments": 45,
      "font_size": 16,
      "export_codec": "h264"
    },
    "files_created": {
      "clips_created": 5,
      "original_clip_paths": [...],
      "subtitled_clips_created": 5,
      "final_clip_paths": [
        "/path/to/subtitled_segment1_vertical.mp4",
        "/path/to/subtitled_segment2_vertical.mp4"
      ],
      "clip_type": "vertical",
      "has_subtitles": true,
      "subtitle_files": {
        "srt": "/path/to/subtitles.srt",
        "vtt": "/path/to/subtitles.vtt"
      }
    }
  }
}
```

## Key Features

- **🚀 Fully Async**: Non-blocking, handles long videos efficiently
- **📊 Progress Tracking**: Real-time progress updates with detailed status
- **📱 Optimal Vertical Cropping**: Direct segment-to-vertical conversion (no double processing)
- **🎯 Speaker Detection**: Smart cropping based on speaker location per segment
- **⚡ High Quality**: Supports up to 8K downloads with single encoding step
- **🧹 Auto Cleanup**: Immediate cleanup of temporary files
- **💾 Storage Efficient**: Minimal temporary storage overhead

## Technical Benefits

### Efficiency Optimizations
- **Single Encoding Step**: Original → Vertical clip (preserves quality)
- **Parallel Processing**: Multiple segments can be processed simultaneously  
- **Memory Efficient**: Only one segment in memory at a time
- **Fast Cleanup**: No leftover files consuming disk space

### Quality Benefits  
- **No Quality Loss**: Direct ffmpeg stream copying for segment extraction
- **Segment-Specific Optimization**: Each clip gets custom speaker detection
- **High Bitrate**: Maintains original video quality throughout processing

## Testing

```bash
cd backend
python test_comprehensive_workflow.py
```

## Modular Design

This workflow focuses on the core video processing. For additional features:

- **Subtitles**: Use `/subtitles` endpoint  
- **Custom Cropping**: Use `/workflow/create-vertical-crop-async`
- **Analysis Only**: Use `/workflow/analyze-only`

---

**🎉 This endpoint delivers the complete path from YouTube URL to viral-ready clips with burned-in subtitles - everything in one call!** 