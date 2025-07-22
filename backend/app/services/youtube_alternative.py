#!/usr/bin/env python3
"""
Alternative YouTube service with multiple Apify actor fallbacks
"""

import logging
import os
from pathlib import Path
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AlternativeYouTubeService:
    """
    Alternative YouTube service with multiple Apify actor fallbacks
    """
    
    def __init__(self):
        self.apify_token = os.getenv("APIFY_TOKEN")
        if not self.apify_token:
            raise ValueError("APIFY_TOKEN environment variable not set")
        
        self.client = ApifyClient(self.apify_token)
        
        # Try multiple actors as fallbacks
        self.actors = [
            "xtech/youtube-video-downloader",  # Original
            "dtrungtin/youtube-downloader",    # Alternative 1
            "webscraper/youtube-downloader",   # Alternative 2
            "apify/youtube-scraper",          # Alternative 3
        ]
    
    async def download_with_fallback(self, url: str, quality: str = "1080p"):
        """
        Try downloading with different actors as fallbacks
        """
        last_error = None
        
        for i, actor_name in enumerate(self.actors):
            try:
                logger.info(f"🎬 Trying actor {i+1}/{len(self.actors)}: {actor_name}")
                
                run_input = {
                    "urls": [url],
                    "resolution": quality,
                    "max_concurrent": 1
                }
                
                # Try to run the actor
                run = self.client.actor(actor_name).call(run_input=run_input)
                
                # Get results
                dataset = self.client.dataset(run["defaultDatasetId"])
                results = dataset.list_items().items
                
                if results and len(results) > 0:
                    video_data = results[0]
                    download_url = video_data.get('download_url')
                    
                    if download_url:
                        logger.info(f"✅ Success with actor: {actor_name}")
                        return {
                            "success": True,
                            "download_url": download_url,
                            "title": video_data.get('title', 'Unknown'),
                            "actor_used": actor_name
                        }
                
                logger.warning(f"⚠️ Actor {actor_name} returned no results")
                
            except Exception as e:
                logger.warning(f"❌ Actor {actor_name} failed: {str(e)}")
                last_error = e
                continue
        
        # All actors failed
        raise Exception(f"All actors failed. Last error: {last_error}")

def test_alternative_actors():
    """Test which actors work with your token"""
    try:
        service = AlternativeYouTubeService()
        
        # Test with a simple video
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        result = service.download_with_fallback(test_url, "720p")
        
        if result["success"]:
            print(f"✅ Working actor found: {result['actor_used']}")
            print(f"📹 Video title: {result['title']}")
            print(f"🔗 Download URL: {result['download_url'][:50]}...")
            return result["actor_used"]
        
    except Exception as e:
        print(f"❌ All actors failed: {e}")
        return None

if __name__ == "__main__":
    test_alternative_actors() 