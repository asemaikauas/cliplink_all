# Azure Blob Storage Integration Guide

This guide explains how to integrate Azure Blob Storage with your Cliplink application for scalable video and clip storage.

## Overview

The Azure Blob Storage integration replaces local file storage with cloud-based storage, providing:

- **Scalability**: No storage limits
- **Durability**: 99.999999999% (11 9's) durability
- **Security**: Built-in encryption and access controls
- **Global Access**: CDN integration for worldwide distribution
- **Cost Efficiency**: Pay-per-use pricing

## Components Added

### 1. Azure Blob Storage Service (`backend/app/services/azure_storage.py`)

Core service for Azure Blob Storage operations:
- File upload/download
- Container management
- SAS URL generation
- Metadata handling
- Secure access controls

### 2. Clip Storage Service (`backend/app/services/clip_storage.py`)

High-level service for clip management:
- Upload clips to Azure
- Generate access URLs
- Manage metadata
- Migration utilities
- Cleanup operations

### 3. Clips API Router (`backend/app/routers/clips.py`)

REST API endpoints for clip operations:
- `GET /clips/{clip_id}` - Get clip information
- `GET /clips/{clip_id}/access-url` - Generate temporary access URL
- `GET /clips/{clip_id}/metadata` - Get detailed metadata
- `DELETE /clips/{clip_id}` - Delete clip
- `GET /videos/{video_id}/clips` - List clips for a video
- `POST /migrate-clips` - Migrate existing clips to Azure

### 4. Database Updates

Updated models and schema:
- Renamed `s3_url` to `blob_url` in clips table
- Added `thumbnail_url` field for clip thumbnails
- Added `file_size` field for better metadata
- Migration script for existing data

## Setup Instructions

### Step 1: Create Azure Storage Account

1. **Create Storage Account**:
   ```bash
   # Using Azure CLI
   az storage account create \
     --name cliplinkstorage \
     --resource-group your-resource-group \
     --location eastus \
     --sku Standard_LRS \
     --allow-blob-public-access false
   ```

2. **Get Connection String**:
   ```bash
   az storage account show-connection-string \
     --name cliplinkstorage \
     --resource-group your-resource-group
   ```

### Step 2: Configure Environment Variables

Add these variables to your `.env` file:

```env
# Azure Blob Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME=cliplinkstorage
AZURE_STORAGE_ACCOUNT_KEY=your-storage-account-key
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=cliplinkstorage;AccountKey=your-key;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=cliplink

# Temporary Directory
TEMP_DIR=/tmp/cliplink
```

### Step 3: Update Dependencies

The required packages are already added to `requirements.txt`:
```
azure-storage-blob==12.19.0
azure-identity==1.15.0
aiofiles==23.2.0
```

Install them:
```bash
pip install -r requirements.txt
```

### Step 4: Run Database Migration

Apply the database migration to update the schema:
```bash
psql -U cliplink -d cliplink -f backend/migrations/001_add_azure_blob_storage.sql
```

### Step 5: Update Main Application

Add the clips router to your main FastAPI application:

```python
# In backend/app/main.py
from .routers import transcript, workflow, subtitles, users, clips

# Include the clips router
app.include_router(clips.router, prefix="/api", tags=["Clips"])
```

## Usage Examples

### 1. Upload a Clip

```python
from app.services.clip_storage import get_clip_storage_service
from app.database import get_db

# In your video processing pipeline
clip_storage = await get_clip_storage_service()
db = await get_db()

clip = await clip_storage.upload_clip(
    clip_file_path="/path/to/clip.mp4",
    video_id="video-uuid",
    start_time=10.0,
    end_time=30.0,
    db=db,
    thumbnail_path="/path/to/thumbnail.jpg"
)
```

### 2. Generate Access URL

```python
# Generate a temporary access URL (expires in 24 hours)
access_url = await clip_storage.generate_clip_access_url(
    clip=clip,
    expiry_hours=24
)
```

### 3. Download Clip

```python
# Download clip to local storage
local_path = await clip_storage.download_clip(
    clip=clip,
    download_dir="/tmp/downloads"
)
```

### 4. API Usage

```bash
# Get clip information
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/clips/clip-uuid

# Generate access URL
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/clips/clip-uuid/access-url?expiry_hours=48

# Get all clips for a video
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/videos/video-uuid/clips
```

## Migration from Local Storage

If you have existing local clips, use the migration endpoint:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/migrate-clips?local_clips_dir=/path/to/clips&batch_size=10"
```

Or use the service directly:

```python
await clip_storage.migrate_local_clips_to_azure(
    local_clips_dir="/path/to/clips",
    db=db,
    batch_size=10
)
```

## Container Organization

The integration creates separate containers for different file types:

- `cliplink-videos`: Original video files
- `cliplink-clips`: Processed clip files
- `cliplink-thumbnails`: Thumbnail images
- `cliplink-temp`: Temporary files

## Security Features

### 1. SAS URLs

All clip access uses SAS (Shared Access Signature) URLs with:
- Time-based expiration
- Specific permissions (read-only by default)
- IP restrictions (optional)

### 2. Private Containers

All containers are private by default - no public access without authentication.

### 3. Metadata Encryption

Sensitive metadata is encrypted at rest in Azure Blob Storage.

## Performance Optimizations

### 1. Parallel Uploads

```python
# Upload multiple clips in parallel
import asyncio

async def upload_clips_parallel(clips_data):
    tasks = []
    for clip_data in clips_data:
        task = clip_storage.upload_clip(**clip_data)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### 2. Chunked Uploads

For large files, use chunked upload:

```python
# Large file upload with progress
async def upload_large_clip(file_path, blob_name):
    azure_storage = await get_azure_storage_service()
    
    # Azure SDK automatically handles chunked uploads for large files
    blob_url = await azure_storage.upload_file(
        file_path=file_path,
        blob_name=blob_name,
        container_type="clips"
    )
    return blob_url
```

### 3. CDN Integration

Configure Azure CDN for faster global access:

```python
# CDN endpoint configuration
CDN_ENDPOINT = "https://cliplink.azureedge.net"

def get_cdn_url(blob_url):
    # Convert blob URL to CDN URL
    return blob_url.replace(
        "https://cliplinkstorage.blob.core.windows.net",
        CDN_ENDPOINT
    )
```

## Cost Management

### 1. Lifecycle Management

Set up automatic lifecycle policies:

```json
{
  "rules": [
    {
      "name": "MoveToIA",
      "enabled": true,
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["cliplink-clips/"]
        },
        "actions": {
          "baseBlob": {
            "tierToCool": {
              "daysAfterModificationGreaterThan": 30
            },
            "tierToArchive": {
              "daysAfterModificationGreaterThan": 90
            }
          }
        }
      }
    }
  ]
}
```

### 2. Storage Tiers

- **Hot**: Frequently accessed clips (first 30 days)
- **Cool**: Occasionally accessed clips (30-90 days)
- **Archive**: Rarely accessed clips (90+ days)

## Monitoring

### 1. Azure Monitor

Set up alerts for:
- Storage usage
- Request rates
- Error rates
- Costs

### 2. Application Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log upload operations
logger.info(f"Uploaded clip {clip_id} to Azure Blob Storage")
logger.info(f"File size: {file_size} bytes")
logger.info(f"Upload duration: {duration}ms")
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check connection string format
   - Verify account key is correct
   - Ensure managed identity is configured

2. **Upload Failures**
   - Check file permissions
   - Verify container exists
   - Check network connectivity

3. **Access URL Issues**
   - Verify SAS token permissions
   - Check expiration time
   - Ensure correct container name

### Debug Mode

Enable debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
azure_logger = logging.getLogger('azure.storage.blob')
azure_logger.setLevel(logging.DEBUG)
```

## Production Considerations

### 1. Redundancy

- Use Geo-redundant storage (GRS) for critical data
- Implement cross-region replication
- Regular backup verification

### 2. Security

- Use Azure Key Vault for secrets
- Implement Azure AD authentication
- Enable audit logging

### 3. Performance

- Use Azure CDN for global distribution
- Implement caching strategies
- Monitor performance metrics

## Integration Checklist

- [ ] Azure Storage Account created
- [ ] Environment variables configured
- [ ] Database migration applied
- [ ] Dependencies installed
- [ ] Clips router added to main app
- [ ] Existing clips migrated (if any)
- [ ] Access permissions configured
- [ ] Monitoring set up
- [ ] Backup strategy implemented
- [ ] Testing completed

## Next Steps

1. **Test the Integration**: Upload and access clips through the API
2. **Monitor Usage**: Set up Azure Monitor alerts
3. **Optimize Costs**: Implement lifecycle policies
4. **Scale**: Configure CDN for global distribution
5. **Secure**: Implement additional security measures

---

This Azure Blob Storage integration provides a robust, scalable foundation for your Cliplink application's file storage needs. The combination of Azure's enterprise-grade storage with your custom clip management logic creates a powerful system for handling video content at scale. 