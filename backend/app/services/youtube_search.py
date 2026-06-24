import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def search_educational_video(query: str, topic_name: str) -> dict | None:
    """
    Finds one relevant educational video for a topic. Biased toward
    longer-form explainer content over shorts/clips via videoDuration filter.
    Returns None if nothing suitable is found or the API call fails.
    """
    if not YOUTUBE_API_KEY:
        return None

    try:
        response = requests.get(YOUTUBE_SEARCH_URL, params={
            "key": YOUTUBE_API_KEY,
            "q": f"{topic_name} {query} explained",
            "part": "snippet",
            "type": "video",
            "videoDuration": "medium",  # 4-20 min — explainer-length, not shorts or full lectures
            "relevanceLanguage": "en",
            "safeSearch": "strict",
            "maxResults": 1,
        }, timeout=6)
        response.raise_for_status()
        items = response.json().get("items", [])

        if not items:
            return None

        item = items[0]
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        return {
            "video_id": video_id,
            "title": snippet.get("title", "")[:120],
            "channel": snippet.get("channelTitle", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }
    except requests.RequestException:
        return None
    


def extract_video_blocks(text: str, topic_name: str) -> tuple[str, list[dict]]:
    """
    Finds ```video {...}``` blocks, retrieves one real video per block,
    returns cleaned text with placeholder markers plus resolved video data.
    """
    videos = []
    pattern = re.compile(r"```video\s*([\s\S]*?)```")

    def replace(match):
        raw = match.group(1).strip()
        try:
            spec = json.loads(raw)
            query = spec.get("query", "").strip()
        except Exception:
            return ""

        if not query:
            return ""

        result = search_educational_video(query, topic_name)
        if not result:
            return ""

        videos.append(result)
        return f"\n[[VIDEO_{len(videos) - 1}]]\n"

    cleaned_text = pattern.sub(replace, text)
    return cleaned_text, videos