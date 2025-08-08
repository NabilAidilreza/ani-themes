import random
from utils import ConfigManager,write_progress
from jikan_client import get_random_title_themes
from yt_client import get_yt_link

config_manager = ConfigManager()
config = config_manager.load()

YOUTUBE_API_KEY = config['YOUTUBE_API_KEY']
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
ANI_THEMES_API_SEARCH_COUNT = config['ANI-THEMES-API-SEARCH-COUNT']
ANI_THEMES_JSON_PLAYLIST_COUNT = config['ANI-THEMES-JSON-PLAYLIST-COUNT']
BLACKLIST = config['BLACKLISTED']

def create_playlist_from_json(filename='saved_yt_links.json', count=ANI_THEMES_JSON_PLAYLIST_COUNT):
    try:
        data_manager = ConfigManager(filename)
        data = data_manager.load()
    except (FileNotFoundError):
        return []
    blacklist = BLACKLIST
    videos = data.get("videos", [])
    if not videos:
        return []
    filtered_videos = [
        video for video in videos
        if all(black.lower() not in video['title'].lower() and black.lower() not in video['url'].lower()
               for black in blacklist)
    ]
    if not filtered_videos:
        #print("[MPV] ⚠ No videos left after applying blacklist.")
        return [], []
    selected = random.sample(filtered_videos, min(count, len(filtered_videos)))
    playlist = [video['url'] for video in selected]
    titles = [(video['title'], video['anime']) for video in selected]
    progress_info = {
        "status": "Completed!",
        "song_name": f"Generated playlist with {len(playlist)} videos (after blacklist).",
        "song_link": ""
    }
    write_progress(progress_info)
    return playlist, titles

def create_playlist_from_api(api_key, yt_search_url, count=ANI_THEMES_API_SEARCH_COUNT):
    collected = set()
    links = []
    blacklist = BLACKLIST
    titles = []

    while len(collected) < count:
        name, themes = get_random_title_themes()
        # Improved blacklist check: case-insensitive substring check
        if name not in collected and all(black.lower() not in name.lower() for black in blacklist):
            collected.add(name)
            print(f"✅ Anime: {name}")
            for opening_title in themes["Openings"]:
                title = opening_title + f" [{name}]"
                print(f"    Added: {title}")
                titles.append(tuple(opening_title,name))
                yt_link,song_title,save_msg = get_yt_link(name, opening_title, api_key, yt_search_url)
                if yt_link:
                    links.append(yt_link)
                else:
                    print(f"⚠ No YouTube link found for {name} - {opening_title}")
        else:
            print(f"⚠ Duplicate or blacklisted found: {name}, skipping...")
    return links, titles
