import random

from helper_functions import ConfigManager
from jikan_fetcher import get_random_title_themes
from yt_finder import get_yt_link,get_yt_links

config_manager = ConfigManager()
config = config_manager.load()

YOUTUBE_API_KEY = config['YOUTUBE_API_KEY']
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
ANI_THEMES_API_SEARCH_COUNT = config['ANI-THEMES-API-SEARCH-COUNT']
ANI_THEMES_JSON_PLAYLIST_COUNT = config['ANI-THEMES-JSON-PLAYLIST-COUNT']
BLACKLIST = config['BLACKLISTED']

def fetch_more_songs():
    jikan_data = get_random_title_themes()
    get_yt_links(jikan_data,YOUTUBE_API_KEY,YOUTUBE_SEARCH_URL)

def create_playlist_from_json(filename='yt_anithemes_links.json', count=ANI_THEMES_JSON_PLAYLIST_COUNT):
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
        print("[MPV] ⚠ No videos left after applying blacklist.")
        return [], []
    selected = random.sample(filtered_videos, min(count, len(filtered_videos)))
    playlist = [video['url'] for video in selected]
    titles = [video['title'] for video in selected]
    print(f"[MPV] 🎵 Generated playlist with {len(playlist)} videos (after blacklist).")
    for title in titles:
        print(title)
    return playlist, titles

def create_playlist_from_api(api_key, yt_search_url, count=ANI_THEMES_API_SEARCH_COUNT):
    collected = set()
    all_openings = []
    blacklist = BLACKLIST
    titles = []
    while len(collected) < count:
        name, themes = get_random_title_themes()
        # Improved blacklist check: case-insensitive substring check
        if name not in collected and all(black.lower() not in name.lower() for black in blacklist):
            collected.add(name)
            print(f"✅ Added: {name}")
            for opening_title in themes["Openings"]:
                title = name + ": " + opening_title 
                titles.append(title)
                yt_link = get_yt_link(name, opening_title, api_key, yt_search_url)
                if yt_link:
                    all_openings.append(yt_link)
                else:
                    print(f"⚠ No YouTube link found for {name} - {opening_title}")
        else:
            print(f"⚠ Duplicate or blacklisted found: {name}, skipping...")
    return all_openings, titles
