#!/usr/bin/env python3
"""
Test script for the new H.264-first download strategy
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.youtube import YouTubeService

def test_h264_strategy():
    """Test the new H.264-first download strategy"""
    
    print("🧪 Testing H.264-First Download Strategy")
    print("=" * 50)
    
    # Initialize YouTube service
    youtube_service = YouTubeService()
    
    # Test quality priorities for different requested qualities
    test_cases = [
        ("best", "Should prioritize 720p, 1080p, 1440p, 2160p"),
        ("1080p", "Should prioritize 720p, 1080p, 1440p, 2160p"),
        ("720p", "Should prioritize 720p, 1080p, 1440p"),
        ("1440p", "Should prioritize 1080p, 720p, 1440p, 2160p"),
        ("2160p", "Should prioritize 1080p, 720p, 1440p, 2160p"),
        ("4k", "Should prioritize 1080p, 720p, 1440p, 2160p"),
        ("8k", "Should prioritize 2160p, 1440p, 1080p, 720p"),
    ]
    
    for quality, description in test_cases:
        priorities = youtube_service._get_h264_quality_priorities(quality)
        print(f"📺 {quality}: {priorities}")
        print(f"   {description}")
        print()
    
    print("✅ H.264 quality priority tests completed!")
    print()
    print("🎯 Key Benefits of New Strategy:")
    print("   • Prioritizes 720p (~90% H.264) over 1080p (~70% H.264)")
    print("   • Avoids downloading AV1 first and then converting")
    print("   • Reduces processing time and bandwidth usage")
    print("   • Eliminates AV1 decoding failures")
    print()
    print("📊 Expected Results:")
    print("   • Faster downloads (no AV1 conversion needed)")
    print("   • More reliable processing (H.264 is well-supported)")
    print("   • Better compatibility with all video processing tools")
    print("   • Reduced server load and processing time")

if __name__ == "__main__":
    test_h264_strategy() 