# HuntAPI Fallback Integration

This document explains the HuntAPI integration that provides a seamless fallback mechanism when the primary Apify YouTube video downloader fails.

## Overview

The ClipLink service now includes automatic fallback to HuntAPI's Video Download endpoint when the Apify actor `xtech/youtube-video-downloader` fails. This ensures higher reliability and uptime for YouTube video processing.

## Architecture

### Primary Service: Apify
- **Service**: Apify YouTube Video Downloader Actor (QrdkHOap2H2LvbyZk)
- **Advantages**: Fast, reliable, good quality options
- **Limitations**: Occasional failures due to YouTube changes or service issues

### Fallback Service: HuntAPI
- **Service**: HuntAPI Video Download API
- **Endpoint**: `GET https://huntapi.com/api/v1/video/download`
- **Advantages**: Alternative infrastructure, good reliability
- **Process**: Asynchronous job-based system with polling

## Integration Points

The HuntAPI fallback is integrated into two key components:

### 1. YouTubeService (`backend/app/services/youtube.py`)
- **Method**: `download_video()`
- **Trigger**: When Apify actor fails with any exception
- **Behavior**: Seamlessly downloads using HuntAPI and continues processing

### 2. SegmentDownloadService (`backend/app/services/segment_downloader.py`)
- **Method**: `_get_video_download_url()`
- **Trigger**: When Apify URL retrieval fails
- **Behavior**: Falls back to HuntAPI to get video download URL

## Setup Instructions

### 1. Environment Variables

Add your HuntAPI token to your environment variables:

```bash
# Option 1: Primary variable name
export HUNTAPI_TOKEN="your_huntapi_token_here"

# Option 2: Alternative variable name
export HUNTAPI_KEY="your_huntapi_token_here"
```

### 2. Get HuntAPI Token

1. Visit [HuntAPI Dashboard](https://docs.huntapi.com/authentication)
2. Create an account or log in
3. Click **API Keys**
4. Select **New**
5. Name your token (e.g., "ClipLink Fallback")
6. Copy the generated token

### 3. Add to Environment File

Add to your `.env` file:

```env
# HuntAPI Configuration
HUNTAPI_TOKEN=your_token_here

# Existing Apify Configuration (keep this)
APIFY_TOKEN=your_apify_token_here
```

### 4. Verify Installation

Run the test script to verify the integration:

```bash
cd backend
python test_huntapi_integration.py
```

## How It Works

### Normal Operation (Apify Success)
```
1. YouTube URL request
2. Apify actor called
3. Video downloaded successfully
4. Processing continues normally
```

### Fallback Operation (Apify Failure)
```
1. YouTube URL request
2. Apify actor called → FAILS
3. HuntAPI fallback triggered
4. HuntAPI job created
5. Job status polled until completion (up to 1 hour)
6. Download URL retrieved
7. Video downloaded successfully
8. Processing continues normally
```

### Quality Mapping

The service automatically maps quality settings between Apify and HuntAPI formats:

| Input Quality | Apify Format | HuntAPI Format |
|---------------|--------------|----------------|
| `8k`          | `2160p`      | `best`         |
| `4k`          | `2160p`      | `best`         |
| `1440p`       | `1440p`      | `best`         |
| `1080p`       | `1080p`      | `1080p`        |
| `720p`        | `720p`       | `720p`         |
| `480p`        | `480p`       | `480p`         |
| `360p`        | `360p`       | `360p`         |
| `best`        | `1080p`      | `best`         |

## Configuration

### Polling Settings

HuntAPI uses an asynchronous job system. The polling configuration can be adjusted in `backend/app/services/huntapi.py`:

```python
class HuntAPIService:
    def __init__(self):
        # Polling configuration
        self.max_poll_time = 3600  # 1 hour max (as per HuntAPI docs)
        self.poll_interval = 30    # 30 seconds between polls
```

### Default Parameters

HuntAPI is configured with defaults that match your current Apify setup:

```python
params = {
    "download_type": "audio_video",  # Full video with audio
    "video_format": "mp4",           # MP4 format
    "video_quality": "best"          # Best available quality
}
```

## Error Handling

### Graceful Degradation
1. **Apify fails** → Try HuntAPI fallback
2. **HuntAPI also fails** → Return original error
3. **HuntAPI unavailable** → Log warning, return original error

### Logging
All fallback attempts are logged with clear indicators:

```
🎬 Starting Apify download: https://youtube.com/... (quality: 1080p)
❌ Apify download failed: [error details]
🔄 Trying HuntAPI fallback for https://youtube.com/...
📋 HuntAPI job created: 0193443f-fb80-9d19-29ba-82bc77c7cd84
📊 HuntAPI job 0193443f... status: QueuedJob
⏳ HuntAPI job 0193443f... still processing, waiting 30s...
📊 HuntAPI job 0193443f... status: CompletedJob
✅ HuntAPI fallback successful: [download_url]
```

## Monitoring

### Success Indicators
- `✅ HuntAPI fallback successful` - Fallback worked
- `📁 Downloaded: [filename]` - File downloaded successfully

### Warning Indicators
- `⚠️ HuntAPI fallback not available` - Service not configured
- `⏳ HuntAPI job still processing` - Normal polling message

### Error Indicators
- `❌ HuntAPI fallback also failed` - Both services failed
- `HuntAPI job timed out` - Job took longer than 1 hour

## Performance Considerations

### Processing Time
- **Apify**: Typically 30 seconds - 5 minutes
- **HuntAPI**: Typically 2-30 minutes (according to docs)
- **Timeout**: 1 hour maximum for HuntAPI jobs

### Cost Considerations
- **HuntAPI Job Creation**: Billable API call
- **HuntAPI Status Polling**: Free (unlimited status checks)
- **Fallback Rate**: Only used when Apify fails

### Bandwidth
- HuntAPI videos are available for 24 hours on their servers
- Downloads happen directly from HuntAPI's signed URLs
- No additional bandwidth through your infrastructure

## Testing

### Manual Testing
```bash
# Test HuntAPI service directly
cd backend
python -c "
import asyncio
from app.services.huntapi import HuntAPIService

async def test():
    huntapi = HuntAPIService()
    url = await huntapi.download_video('https://youtube.com/watch?v=dQw4w9WgXcQ', '720p')
    print(f'Success: {url}')

asyncio.run(test())
"
```

### Integration Testing
```bash
# Run the comprehensive test suite
cd backend
python test_huntapi_integration.py
```

## Troubleshooting

### Common Issues

#### 1. "HUNTAPI_TOKEN environment variable not set"
**Solution**: Add your HuntAPI token to environment variables or `.env` file

#### 2. "HuntAPI fallback not available"
**Solution**: 
- Check token is correctly set
- Verify `huntapi.py` is in the services directory
- Check imports are working

#### 3. "HuntAPI job timed out after 3600 seconds"
**Solution**: 
- This is normal for very long videos or high server load
- Video may be processed successfully but took longer than expected
- Check HuntAPI dashboard for job status

#### 4. Both Apify and HuntAPI fail
**Solutions**:
- Check if video is private, age-restricted, or unavailable
- Verify both API tokens are valid
- Check network connectivity
- Try a different YouTube URL for testing

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger('app.services.huntapi').setLevel(logging.DEBUG)
logging.getLogger('app.services.youtube').setLevel(logging.DEBUG)
```

## API Reference

### HuntAPIService Methods

#### `download_video(url: str, quality: str = "best") -> str`
Downloads a YouTube video and returns the download URL.

**Parameters:**
- `url`: YouTube video URL
- `quality`: Video quality preference

**Returns:** Direct download URL to the MP4 file

**Raises:** `HuntAPIError` if download fails

#### `_create_download_job(url: str, quality: str) -> str`
Creates a download job and returns job ID.

#### `_poll_job_completion(job_id: str) -> str`
Polls job status until completion and returns download URL.

## Security Considerations

- HuntAPI tokens should be kept secure and not committed to version control
- Use environment variables or secure secret management
- Regularly rotate API tokens
- Monitor API usage for unexpected charges

## Future Enhancements

### Potential Improvements
1. **Multiple Fallbacks**: Add more YouTube download services
2. **Smart Routing**: Choose service based on video characteristics
3. **Caching**: Cache successful download URLs
4. **Health Checks**: Monitor service availability
5. **Metrics**: Track fallback usage rates

### Configuration Options
1. **Priority Order**: Configure which service to try first
2. **Timeout Customization**: Adjust polling intervals per video type
3. **Quality Preferences**: Set service-specific quality preferences

## Support

If you encounter issues with the HuntAPI integration:

1. Check the logs for error messages
2. Run the test script for diagnosis
3. Verify environment variables are set correctly
4. Check [HuntAPI Status Page](https://docs.huntapi.com/status) for service health
5. Review [HuntAPI Documentation](https://docs.huntapi.com/) for API updates

## Changelog

### v1.0.0 (Current)
- ✅ Initial HuntAPI integration
- ✅ Automatic fallback from Apify failures
- ✅ Quality mapping between services
- ✅ Comprehensive error handling
- ✅ Integration test suite
- ✅ Full documentation 