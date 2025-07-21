#!/bin/bash
"""
Quick test script for conda-forge AV1 support setup
"""

set -e

echo "🐍 Building ClipLink with conda-forge OpenCV AV1 support..."

# Build the new Docker image
echo "📦 Building Docker image..."
docker build -t cliplink-backend-conda backend/

echo "🧪 Testing conda-forge OpenCV setup..."
docker run --rm cliplink-backend-conda python test_av1_support.py

echo "🔍 Checking OpenCV version and build info..."
docker run --rm cliplink-backend-conda python -c "
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

echo "✅ conda-forge setup complete!"
echo ""
echo "🎯 To test with an actual AV1 video:"
echo "   docker run -v /path/to/your/av1/video:/test_video -it cliplink-backend-conda \\"
echo "     python test_av1_support.py /test_video/your_av1_file.mp4"
echo ""
echo "🚀 Your timeout issues with AV1 should now be resolved!" 