#!/bin/bash
"""
Quick test script for Apify + conda-forge setup
Tests both YouTube downloads (Apify) and AV1 support (conda-forge)
"""

set -e

echo "🚀 Building ClipLink with Apify + conda-forge integration..."

# Build the new Docker image
echo "📦 Building Docker image..."
docker build -t cliplink-backend-apify-conda backend/

echo "🧪 Testing Apify YouTube integration..."
docker run --rm -e APIFY_TOKEN="${APIFY_TOKEN}" cliplink-backend-apify-conda python test_apify_youtube.py

echo "🧪 Testing conda-forge OpenCV AV1 support..."
docker run --rm cliplink-backend-apify-conda python test_av1_support.py

echo "🔍 Checking OpenCV version and build info..."
docker run --rm cliplink-backend-apify-conda python -c "
import cv2
print(f'OpenCV Version: {cv2.__version__}')
build_info = cv2.getBuildInformation()
print('AV1 Support Indicators:')
for indicator in ['libavcodec', 'dav1d', 'aom']:
    if indicator.lower() in build_info.lower():
        print(f'  ✅ {indicator}: Found')
    else:
        print(f'  ❌ {indicator}: Not found')
"

echo "✅ Apify + conda-forge setup complete!"
echo ""
echo "📋 Configuration check:"
if [ -z "$APIFY_TOKEN" ]; then
    echo "   ⚠️ APIFY_TOKEN not set - make sure to configure in your .env file"
else
    echo "   ✅ APIFY_TOKEN configured"
fi
echo ""
echo "🎯 To test with an actual AV1 video:"
echo "   docker run -v /path/to/your/av1/video:/test_video -it cliplink-backend-apify-conda \\"
echo "     python test_av1_support.py /test_video/your_av1_file.mp4"
echo ""
echo "🚀 Complete solution implemented:"
echo "   - Reliable YouTube downloads via Apify (no yt-dlp issues)"
echo "   - Native AV1 support via conda-forge (no timeout issues)" 