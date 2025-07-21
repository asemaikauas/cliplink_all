#!/usr/bin/env python3
"""
Test script for the new H.264-first download strategy with quality prioritization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.youtube import YouTubeService

def test_h264_strategy():
    """Test the new H.264-first download strategy with quality prioritization"""
    
    print("🧪 Testing H.264-First Download Strategy (Quality Prioritized)")
    print("=" * 60)
    
    # Initialize YouTube service
    youtube_service = YouTubeService()
    
    # Test quality priorities for different requested qualities
    test_cases = [
        ("best", "Should prioritize: 2160p → 1440p → 1080p → 720p"),
        ("1080p", "Should prioritize: 1080p → 720p → 1440p → 2160p"),
        ("720p", "Should prioritize: 720p → 1080p → 1440p"),
        ("1440p", "Should prioritize: 1440p → 1080p → 720p → 1440p → 2160p"),
        ("2160p", "Should prioritize: 2160p → 1080p → 720p → 1440p → 2160p"),
        ("4k", "Should prioritize: 4k → 1080p → 720p → 1440p → 2160p"),
        ("8k", "Should prioritize: 2160p → 1440p → 1080p → 720p"),
    ]
    
    for quality, description in test_cases:
        priorities = youtube_service._get_h264_quality_priorities(quality)
        print(f"📺 {quality}: {priorities}")
        print(f"   {description}")
        print()
    
    print("✅ H.264 quality priority tests completed!")
    print()
    print("🎯 New Strategy Benefits:")
    print("   • Prioritizes requested quality first (user gets what they want)")
    print("   • Falls back to lower qualities if AV1 is detected")
    print("   • Still avoids AV1 conversion issues")
    print("   • Best of both worlds: quality + reliability")
    print()
    print("📊 How it works:")
    print("   1. Try requested quality first (e.g., 1080p)")
    print("   2. If it's H.264 → Use it ✅")
    print("   3. If it's AV1 → Try next quality (e.g., 720p)")
    print("   4. Repeat until H.264 is found")
    print("   5. If no H.264 found → Use original with conversion warning")
    print()
    print("🚀 Expected Results:")
    print("   • Users get highest quality available")
    print("   • Faster processing (no AV1 conversion needed)")
    print("   • More reliable video processing")
    print("   • Better user experience")

if __name__ == "__main__":
    test_h264_strategy() 