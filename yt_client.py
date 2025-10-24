import os
import json
import requests
from utils import ConfigManager,write_progress
from rich_console import failure


def save_unique_youtube_video(anime_name, title, url, filename="resources/saved_yt_links.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                videos = data.get("videos", [])
            except json.JSONDecodeError:
                videos = []
    else:
        videos = []

    # Build quick lookup maps
    title_to_url = {video["title"]: video["url"] for video in videos}
    url_set = {video["url"] for video in videos}

    # If title already exists, do not overwrite
    if title in title_to_url:
        return "[Previously Saved - Title exists]"

    # If URL already exists under another title, also ignore
    if url in url_set:
        return "[Previously Saved - URL exists]"

    # Save new entry
    videos.append({"anime": anime_name, "title": title, "url": url})
    with open(filename, "w", encoding='utf-8') as f:
        json.dump({"videos": videos}, f, indent=4, ensure_ascii=False)

    return "[Saved]"
    
def get_yt_link(anime_name,title,api_key,yt_search_url): 
    config_manager = ConfigManager()
    config = config_manager.load()
    query = title.replace('"', '')  # Clean up quotes
    params = {
        'part': 'snippet',
        'q': f'{query} anime op',
        'type': 'video',
        'order': 'relevance',
        'safeSearch': 'strict',
        'key': api_key,
        'maxResults': 1
    }
    config["YOUTUBE_API_CALL_COUNTER"] += 1
    with open("resources/config.json", "w") as f:
        json.dump(config, f, indent=2)

    yt_response = requests.get(yt_search_url, params=params).json()
    items = yt_response.get('items')
    if items:
        video_id = items[0]['id']['videoId']
        song_title = items[0]['snippet']['title']
        url = f"https://www.youtube.com/watch?v={video_id}"
        progress_info = {
            "status": "Processing...",
            "song_name": song_title,
            "song_link": url
        }
        write_progress(progress_info)
        save_msg = save_unique_youtube_video(anime_name,title,url)
        return url,song_title,save_msg
    else:
        failure(f"No YouTube result found for: {query}")
        return "","",""

# def get_yt_links(jikan_data, api_key, yt_search_url):
#     config_manager = ConfigManager()
#     config = config_manager.load()
#     anime_name = jikan_data[0]
#     openings = jikan_data[1]["Openings"]
#     for op in openings:
#         query = op.replace('"', '')
#         params = {
#             'part': 'snippet',
#             'q': f'{query} official anime opening creditless',
#             'type': 'video',
#             'order': 'relevance',
#             'safeSearch': 'strict',
#             'key': api_key,
#             'maxResults': 1
#         }
#         try:
#             yt_response = requests.get(yt_search_url, params=params)
#             yt_response.raise_for_status()
#             data = yt_response.json()
#             items = data.get('items')
#             if items:
#                 video_id = items[0]['id']['videoId']
#                 song_title = items[0]['snippet']['title']
#                 url = f"https://www.youtube.com/watch?v={video_id}"
#                 save_msg = save_unique_youtube_video(anime_name, song_title, url)
#             else:
#                 print(f"No YouTube result found for: {query}")

#             # Increment counter after the request
#             config["YOUTUBE_API_CALL_COUNTER"] += 1
#             with open("resources/config.json", "w") as f:
#                 json.dump(config, f, indent=2)

#         except requests.RequestException as e:
#             print(f"Request failed for {query}: {e}")

