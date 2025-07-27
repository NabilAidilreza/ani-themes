import os
import json
import requests
from helper_functions import ConfigManager

def save_unique_youtube_video(anime_name, title, url, filename="yt_anithemes_links.json"):
    if os.path.exists(filename):
        with open(filename, "r",encoding="utf-8") as f:
            try:
                data = json.load(f)
                videos = data.get("videos", [])
            except json.JSONDecodeError:
                videos = []
    else:
        videos = []

    # Check if URL already exists
    existing_urls = {video["url"] for video in videos}
    if url not in existing_urls:
        videos.append({"anime":anime_name,"title": title, "url": url})
        with open(filename, "w",encoding='utf-8') as f:
            json.dump({"videos": videos}, f, indent=4, ensure_ascii=False)
        print(f"🎶 {title}: {url} [Saved]")
    else:
        print(f"🎶 {title}: {url} [Exist => Skip]")

def get_yt_links(jikan_data, api_key, yt_search_url):
    config_manager = ConfigManager()
    config = config_manager.load()
    # with open('config.json') as f:
    #     config = json.load(f)

    anime_name = jikan_data[0]
    openings = jikan_data[1]["Openings"]
    for op in openings:
        query = op.replace('"', '')
        params = {
            'part': 'snippet',
            'q': f'{query} op creditless -official music video -MV',
            'type': 'video',
            'key': api_key,
            'maxResults': 1
        }
        try:
            yt_response = requests.get(yt_search_url, params=params)
            yt_response.raise_for_status()
            data = yt_response.json()
            items = data.get('items')
            if items:
                video_id = items[0]['id']['videoId']
                song_title = items[0]['snippet']['title']
                url = f"https://www.youtube.com/watch?v={video_id}"
                save_unique_youtube_video(anime_name, song_title, url)
            else:
                print(f"No YouTube result found for: {query}")

            # Increment counter after the request
            config["YOUTUBE_API_CALL_COUNTER"] += 1
            with open("config.json", "w") as f:
                json.dump(config, f, indent=2)

        except requests.RequestException as e:
            print(f"Request failed for {query}: {e}")

def get_yt_link(anime_name,title,api_key,yt_search_url): 
    config_manager = ConfigManager()
    config = config_manager.load()
    query = title.replace('"', '')  # Clean up quotes
    params = {
        'part': 'snippet',
        'q': f'{query} op creditless -official music video -MV',
        'type': 'video',
        'key': api_key,
        'maxResults': 1
    }
    config["YOUTUBE_API_CALL_COUNTER"] += 1
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
        f.close()
    yt_response = requests.get(yt_search_url, params=params).json()
    items = yt_response.get('items')
    if items:
        video_id = items[0]['id']['videoId']
        song_title = items[0]['snippet']['title']
        url = f"https://www.youtube.com/watch?v={video_id}"
        save_unique_youtube_video(anime_name,song_title,url)
        return url
    else:
        print(f"No YouTube result found for: {query}")
        return ""
