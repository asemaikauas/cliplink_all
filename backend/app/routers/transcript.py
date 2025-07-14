from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.youtube import get_video_id
from app.services.transcript import fetch_youtube_transcript, extract_full_transcript
from app.services.gemini import analyze_transcript_with_gemini

router = APIRouter()

class TranscriptRequest(BaseModel):
    youtube_url: str

@router.post("/transcript")
def get_transcript(req: TranscriptRequest):
    """
    Extract transcript from YouTube URL
    Returns: video title, category, description, transcript, timecodes
    """
    try:
        video_id = get_video_id(req.youtube_url)
        data = fetch_youtube_transcript(video_id)
        transcript_data = extract_full_transcript(data)
        
        if isinstance(transcript_data, dict) and 'error' in transcript_data:
            return transcript_data
        
        return transcript_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")  
async def analyze_video(req: TranscriptRequest):
    """
    Extract transcript from YouTube URL and analyze with Gemini to generate viral video segments
    """
    try:
        video_id = get_video_id(req.youtube_url)
        
        # Step 2: Fetch transcript from YouTube API
        data = fetch_youtube_transcript(video_id)
        transcript_data = extract_full_transcript(data)
        
        # Step 3: Check if we got an error from transcript extraction
        if isinstance(transcript_data, dict) and 'error' in transcript_data:
            return transcript_data
        
        # Step 4: Analyze with Gemini AI
        analysis_result = await analyze_transcript_with_gemini(transcript_data)
        
        return analysis_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))