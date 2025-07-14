#!/usr/bin/env python3
"""Test CapCut-style subtitle generation."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.subs import SubtitleProcessor

def test_capcut_mode():
    """Test CapCut-style punch word generation."""
    
    print("🎬 Testing CapCut-Style Subtitle Generation...")
    print("="*60)
    
    # Create processor in CapCut mode
    processor = SubtitleProcessor(
        capcut_mode=True,
        min_word_duration_ms=800,
        max_word_duration_ms=1500,
        word_overlap_ms=150
    )
    
    # Test data similar to your example
    test_segments = [
        {
            'text': 'you know, an agent, a chat tool on the side to say, hey, you know, this is how you can learn',
            'start': 0.0,
            'end': 4.8
        },
        {
            'text': 'coding. This is kind of how you can fix your bugs.',
            'start': 4.8,
            'end': 7.5
        }
    ]
    
    print(f"📝 Input segments:")
    for i, seg in enumerate(test_segments, 1):
        print(f"   [{i}] {seg['start']:.1f}s - {seg['end']:.1f}s: '{seg['text']}'")
    print()
    
    # Process segments
    final_segments = processor.process_segments(test_segments)
    
    print(f"🎯 CapCut Output ({len(final_segments)} punch-word segments):")
    print("="*60)
    
    for i, segment in enumerate(final_segments, 1):
        start_time = f"{segment.start_time:.3f}s"
        end_time = f"{segment.end_time:.3f}s"
        duration = segment.end_time - segment.start_time
        
        print(f"[{i:2d}] {start_time:>8} --> {end_time:>8} ({duration:.3f}s)  \"{segment.text}\"")
    
    print("\n" + "="*60)
    
    # Analysis
    total_original_duration = sum(seg['end'] - seg['start'] for seg in test_segments)
    
    # Check for overlaps
    overlaps = 0
    for i in range(len(final_segments) - 1):
        current_end = final_segments[i].end_time
        next_start = final_segments[i + 1].start_time
        if current_end > next_start:
            overlaps += 1
    
    # Check word count per segment
    words_per_segment = [len(seg.text.split()) for seg in final_segments]
    avg_words = sum(words_per_segment) / len(words_per_segment)
    max_words = max(words_per_segment)
    
    print(f"📊 Analysis:")
    print(f"   Original segments: {len(test_segments)}")
    print(f"   CapCut segments: {len(final_segments)}")
    print(f"   Expansion ratio: {len(final_segments) / len(test_segments):.1f}x")
    print(f"   Total duration: {total_original_duration:.1f}s")
    print(f"   Overlapping segments: {overlaps}")
    print(f"   Words per segment: {avg_words:.1f} avg, {max_words} max")
    print(f"   Duration range: {min(seg.end_time - seg.start_time for seg in final_segments):.3f}s - {max(seg.end_time - seg.start_time for seg in final_segments):.3f}s")
    
    # Check if it meets CapCut criteria
    success = True
    issues = []
    
    if max_words > 7:
        success = False
        issues.append(f"Some segments have >7 words (max: {max_words}) - chunks too large")
    
    if overlaps > 0:
        success = False
        issues.append("Found overlapping segments (sequential mode should have no overlaps)")
    
    # Check for reasonable chunking (not too many tiny segments, not too few huge ones)
    avg_words_per_chunk = sum(len(seg.text.split()) for seg in final_segments) / len(final_segments)
    if avg_words_per_chunk < 2.5:
        success = False
        issues.append(f"Chunks too small on average ({avg_words_per_chunk:.1f} words/chunk)")
    elif avg_words_per_chunk > 6:
        success = False
        issues.append(f"Chunks too large on average ({avg_words_per_chunk:.1f} words/chunk)")
    
    print(f"\n🎯 CapCut Mode Test: {'✅ PASSED' if success else '❌ FAILED'}")
    if issues:
        for issue in issues:
            print(f"   ⚠️ {issue}")
    
    return success

def test_traditional_mode():
    """Test traditional mode for comparison."""
    
    print("\n📝 Testing Traditional Mode for Comparison...")
    print("="*60)
    
    # Create processor in traditional mode
    processor = SubtitleProcessor(
        capcut_mode=False,
        max_chars_per_line=50,
        max_lines=2
    )
    
    test_segments = [
        {
            'text': 'you know, an agent, a chat tool on the side to say, hey, you know, this is how you can learn',
            'start': 0.0,
            'end': 4.8
        }
    ]
    
    # Process segments
    final_segments = processor.process_segments(test_segments)
    
    print(f"📝 Traditional Output ({len(final_segments)} segments):")
    for i, segment in enumerate(final_segments, 1):
        print(f"[{i}] {segment.start_time:.1f}s - {segment.end_time:.1f}s:")
        lines = segment.text.split('\n')
        for line in lines:
            print(f"    {line}")
        print()
    
    return len(final_segments) >= 1

if __name__ == "__main__":
    print("🚀 Running CapCut Subtitle Mode Tests...\n")
    
    # Test CapCut mode
    capcut_success = test_capcut_mode()
    
    # Test traditional mode
    traditional_success = test_traditional_mode()
    
    print("🎯 Final Results:")
    print(f"   CapCut Mode: {'✅ PASSED' if capcut_success else '❌ FAILED'}")
    print(f"   Traditional Mode: {'✅ PASSED' if traditional_success else '❌ FAILED'}")
    
    if capcut_success and traditional_success:
        print("\n🎉 All tests passed! CapCut mode is ready for viral content!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed! Check the implementation.")
        sys.exit(1) 