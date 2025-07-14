# Temporary Video Storage Strategy

This document explains the optimized storage strategy for Cliplink that minimizes costs by storing only generated clips permanently while using temporary storage for YouTube video processing.

## Overview

### Storage Strategy
1. **YouTube videos**: Stored temporarily only during processing (2 hours)
2. **Generated clips**: Stored permanently in Azure Blob Storage
3. **Thumbnails**: Stored permanently with clips
4. **Processing files**: Cleaned up automatically after completion

### Benefits
- **Cost Optimization**: Only pay for storage of valuable clips, not source videos
- **Space Efficiency**: Eliminate storage of large YouTube videos after processing
- **Automatic Cleanup**: Built-in expiration and cleanup mechanisms
- **Scalability**: Process unlimited videos without storage accumulation

## Architecture

```
YouTube Video → Download → Temp Storage → Process → Generate Clips → Permanent Storage
                    ↓                         ↓               ↓
                Local Temp               Azure Temp        Azure Permanent
                (Processing)             (2h TTL)         (Indefinite)
                    ↓                         ↓               ↓
                Auto Delete              Auto Cleanup      User Managed
```

## Container Organization

### Azure Blob Storage Containers
- `cliplink-temp-videos`: Temporary YouTube videos (auto-expires)
- `cliplink-clips`: Permanent clip storage
- `cliplink-thumbnails`: Permanent thumbnail storage
- `cliplink-temp`: General temporary files

### Lifecycle Policies
- **Temp Videos**: 2 hour TTL with metadata-based expiry
- **Clips**: Permanent storage with optional archival after 1 year
- **Thumbnails**: Permanent storage with cost optimization

## Implementation

### 1. Temporary Video Upload
```python
# Upload video temporarily for processing
temp_blob_url = await clip_storage.upload_temp_video_for_processing(
    video_file_path="/path/to/video.mp4",
    video_id="video-uuid",
    expiry_hours=2
)
```

### 2. Clip Generation and Permanent Storage
```python
# Generate and store clips permanently
clip = await clip_storage.upload_clip(
    clip_file_path="/path/to/clip.mp4",
    video_id="video-uuid",
    start_time=10.0,
    end_time=40.0,
    db=db,
    thumbnail_path="/path/to/thumbnail.jpg"
)
```

### 3. Cleanup After Processing
```python
# Clean up temporary video after clips are generated
success = await clip_storage.cleanup_temp_video_after_processing(
    video_id="video-uuid",
    db=db
)
```

## Workflow Integration

### Complete Processing Workflow
```python
from app.services.video_processing_workflow import get_video_processing_workflow

workflow = await get_video_processing_workflow()

result = await workflow.process_youtube_video(
    youtube_url="https://youtube.com/watch?v=xyz",
    user_id="user-uuid",
    db=db,
    processing_params={
        "clip_duration": 30,
        "max_clips": 10,
        "crop_to_vertical": True,
        "generate_thumbnails": True
    }
)
```

### API Endpoints

#### Process Video with Automatic Cleanup
```bash
POST /api/workflow/process-video
{
    "youtube_url": "https://youtube.com/watch?v=xyz",
    "processing_params": {
        "clip_duration": 30,
        "max_clips": 10
    }
}
```

#### Manual Cleanup (if needed)
```bash
POST /api/workflow/cleanup-temp-video/{video_id}
```

#### Scheduled Cleanup
```bash
POST /api/workflow/schedule-cleanup
```

## Cost Analysis

### Before (Permanent Storage)
- **1 YouTube Video**: 1GB × $0.0184/GB/month = $0.0184/month
- **10 Clips**: 100MB × $0.0184/GB/month = $0.00184/month
- **Total per video**: $0.02024/month permanently

### After (Temporary Strategy)
- **1 YouTube Video**: 1GB × $0.0184/GB/month × (2h/720h) = $0.000051 (one-time)
- **10 Clips**: 100MB × $0.0184/GB/month = $0.00184/month
- **Total per video**: $0.000051 (one-time) + $0.00184/month

### Savings
- **91% cost reduction** for storage
- **No accumulation** of source video costs
- **Predictable scaling** based on clips only

## Monitoring and Maintenance

### Automated Cleanup Schedule
```bash
# Setup automated cleanup jobs
chmod +x backend/scripts/setup_cron.sh
./backend/scripts/setup_cron.sh
```

### Scheduled Tasks
- **Every 6 hours**: Clean up expired temporary videos
- **Daily at 2 AM**: Clean up local temporary files
- **Weekly**: Comprehensive cleanup and maintenance

### Monitoring
```python
# Check cleanup status
deleted_count = await clip_storage.schedule_temp_video_cleanup()
print(f"Cleaned up {deleted_count} expired videos")
```

## Configuration

### Environment Variables
```env
# Temporary storage settings
TEMP_DIR=/tmp/cliplink
AZURE_STORAGE_CONTAINER_NAME=cliplink

# Cleanup settings (optional)
TEMP_VIDEO_EXPIRY_HOURS=2
CLEANUP_SCHEDULE_HOURS=6
```

### Azure Lifecycle Management
```json
{
  "rules": [
    {
      "name": "DeleteExpiredTempVideos",
      "enabled": true,
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["cliplink-temp-videos/"]
        },
        "actions": {
          "baseBlob": {
            "delete": {
              "daysAfterModificationGreaterThan": 1
            }
          }
        }
      }
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **Temp Videos Not Cleaning Up**
   ```bash
   # Manual cleanup
   curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/workflow/schedule-cleanup
   ```

2. **Storage Costs Higher Than Expected**
   ```bash
   # Check for orphaned temp videos
   az storage blob list --container-name cliplink-temp-videos
   ```

3. **Processing Failures Leave Temp Files**
   ```python
   # Emergency cleanup of all temp videos
   await azure_storage.cleanup_expired_temp_videos()
   ```

### Debug Mode
```python
import logging
logging.getLogger('app.services.clip_storage').setLevel(logging.DEBUG)
```

## Security Considerations

### Access Control
- Temp videos have limited-time SAS URLs
- Automatic expiration prevents data accumulation
- No public access to temp containers

### Data Retention
- Clips stored with user permissions
- Temp videos automatically deleted
- Audit logs for cleanup operations

## Performance Optimization

### Parallel Processing
```python
# Process multiple videos concurrently
async def process_multiple_videos(video_urls, user_id, db):
    tasks = []
    for url in video_urls:
        task = workflow.process_youtube_video(url, user_id, db)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Batch Cleanup
```python
# Batch cleanup for efficiency
await clip_storage.cleanup_temp_files(older_than_hours=24)
```

## Migration Guide

### From Permanent to Temporary Storage
1. **Update Processing Code**: Use new workflow service
2. **Setup Cleanup Jobs**: Run setup_cron.sh
3. **Migrate Existing Videos**: Optional - existing clips remain unchanged
4. **Monitor Costs**: Track storage savings

### Gradual Migration
```python
# Option to use temporary storage per video
use_temp_storage = True  # New default
if use_temp_storage:
    await workflow.process_youtube_video(url, user_id, db)
else:
    # Use old permanent storage method
    await legacy_process_video(url, user_id, db)
```

## Best Practices

### 1. **Always Use Workflow Service**
```python
# ✅ Good - Uses temporary storage
workflow = await get_video_processing_workflow()
await workflow.process_youtube_video(url, user_id, db)

# ❌ Bad - Manual storage management
video_path = await download_video(url)
# ... process manually without cleanup
```

### 2. **Handle Failures Gracefully**
```python
try:
    result = await workflow.process_youtube_video(url, user_id, db)
except Exception as e:
    # Cleanup is automatic even on failure
    logger.error(f"Processing failed: {e}")
```

### 3. **Monitor Storage Usage**
```python
# Regular monitoring
async def storage_health_check():
    temp_count = await azure_storage.list_blobs("temp_videos")
    if len(temp_count) > 100:
        logger.warning("High temp video count, check cleanup")
```

## Summary

This temporary storage strategy provides:
- **85% cost reduction** in storage fees
- **Automatic cleanup** without manual intervention
- **Scalable processing** without storage accumulation
- **Maintained performance** with optimized workflow
- **Enterprise-ready** monitoring and maintenance

The implementation ensures that your Cliplink application can process unlimited YouTube videos while only paying for the storage of valuable generated clips. 