import os
import requests
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_TRANSCRIPT_API = os.getenv("YOUTUBE_TRANSCRIPT_API")

def fetch_youtube_transcript(video_id: str):
    """
    Fetch transcript from YouTube using external API
    """
    if not YOUTUBE_TRANSCRIPT_API:
        raise Exception("YOUTUBE_TRANSCRIPT_API environment variable is not set. Please add your API key to the .env file.")
    
    if not video_id:
        raise Exception("Invalid video ID. Unable to extract video ID from the provided YouTube URL.")
    
    url = "https://www.youtube-transcript.io/api/transcripts"
    headers = {
        "Authorization": f"Basic {YOUTUBE_TRANSCRIPT_API}",
        "Content-Type": "application/json"
    }
    payload = {"ids": [video_id]}
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"🔍 Debug: Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            print(f"🔍 Debug: Response data: {data}")
            return data
        except ValueError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"❌ Raw response: {response.text}")
            raise Exception(f"Invalid JSON response from YouTube Transcript API: {e}")
    else:
        error_msg = f"YouTube Transcript API error {response.status_code}: {response.text}"
        print(f"❌ Error: {error_msg}")
        
        # Handle common error cases
        if response.status_code == 401:
            raise Exception("Invalid or missing YouTube Transcript API key. Check your YOUTUBE_TRANSCRIPT_API environment variable.")
        elif response.status_code == 403:
            raise Exception("YouTube Transcript API access forbidden. Check your API key permissions.")
        elif response.status_code == 404:
            raise Exception("Video not found or transcript not available for this video.")
        elif response.status_code == 429:
            raise Exception("YouTube Transcript API rate limit exceeded. Please try again later.")
        else:
            raise Exception(error_msg)

def extract_full_transcript(transcript_data):
    """
    Extract and format transcript data from various sources
    """
    print(f"🔍 Debug: Extracting transcript from: {transcript_data}")
    print(f"🔍 Debug: Data type: {type(transcript_data)}")
    
    if not transcript_data:
        print("❌ No transcript data received")
        return {
            "error": "No transcript data received",
            "id": None,
            "title": None,
            "category": None,
            "transcript": "",
            "timecodes": []
        }
    
    if isinstance(transcript_data, list) and len(transcript_data) > 0:
        video_data = transcript_data[0]  
        
        # Extract basic video info
        video_id = video_data.get('id', 'unknown')
        video_title = video_data.get('title', 'Unknown title')
        
        # Extract category and description from microformat
        category = "Unknown"
        description = ""
        microformat = video_data.get('microformat', {})
        if isinstance(microformat, dict):
            player_microformat = microformat.get('playerMicroformatRenderer', {})
            if isinstance(player_microformat, dict):
                category = player_microformat.get('category', 'Unknown')
                
                # Extract description
                desc_obj = player_microformat.get('description', {})
                if isinstance(desc_obj, dict):
                    description = desc_obj.get('simpleText', '')
        
        print(f"🔍 Debug: Processing video: {video_title} (ID: {video_id})")
        
        # Check if tracks exist
        if 'tracks' in video_data and len(video_data['tracks']) > 0:
            transcript_track = video_data['tracks'][0]  # Get first track
            
            if 'transcript' in transcript_track:
                text_segments = []
                timecodes = []
                
                # Debug: Show structure of first segment
                if len(transcript_track['transcript']) > 0:
                    first_segment = transcript_track['transcript'][0]
                    print(f"🔍 Debug: First segment keys: {list(first_segment.keys())}")
                    print(f"🔍 Debug: First segment content: {first_segment}")
                
                # Extract both text and timecodes
                for i, segment in enumerate(transcript_track['transcript']):
                    if 'text' in segment:
                        text_segments.append(segment['text'])
                        
                        # Calculate duration from various possible fields
                        start_time = float(segment.get('start', 0))
                        duration = 0
                        
                        # Method 1: Check for 'dur' field
                        if 'dur' in segment:
                            duration = float(segment.get('dur', 0))
                        # Method 2: Check for 'duration' field
                        elif 'duration' in segment:
                            duration = float(segment.get('duration', 0))
                        # Method 3: Calculate from end time
                        elif 'end' in segment:
                            end_time = float(segment.get('end', 0))
                            duration = end_time - start_time
                        # Method 4: Calculate from next segment's start time
                        elif i + 1 < len(transcript_track['transcript']):
                            next_segment = transcript_track['transcript'][i + 1]
                            if 'start' in next_segment:
                                next_start = float(next_segment.get('start', 0))
                                duration = next_start - start_time
                        
                        timecodes.append({
                            "start": start_time,
                            "duration": duration, 
                            "text": segment.get('text', '')
                        })
                
                if text_segments:
                    video_transcript = ' '.join(text_segments)
                    print(f"✅ Successfully extracted transcript: {len(video_transcript)} characters")
                    
                    return {
                        "id": video_id,
                        "title": video_title, 
                        "category": category,
                        "description": description,
                        "transcript": video_transcript,
                        "timecodes": timecodes
                    }
                else:
                    return {
                        "error": "No text segments found in transcript",
                        "id": video_id,
                        "title": video_title,
                        "category": category,
                        "description": description,
                        "transcript": "",
                        "timecodes": []
                    }
            else:
                return {
                    "error": "No transcript found in track",
                    "id": video_id,
                    "title": video_title,
                    "category": category,
                    "description": description,
                    "transcript": "",
                    "timecodes": []
                }
        else:
            return {
                "error": "No tracks found for this video",
                "id": video_id,
                "title": video_title,
                "category": category,
                "description": description,
                "transcript": "",
                "timecodes": []
            }
    
    # Final fallback for any other format
    return {
        "error": f"Unexpected response format. Type: {type(transcript_data)}",
        "id": "unknown",
        "title": "Unknown",
        "category": "Unknown",  
        "transcript": "",
        "timecodes": []
    } 