import re
import requests
import random
from time import sleep

def fetch_jikan(api,params):
    try:
        return requests.get(api, params=params).json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except ValueError as e:
        print(f"JSON decoding failed: {e}")
        return None
    
def get_random_title_themes(num = 10):
    JIKAN_TOP = "https://api.jikan.moe/v4/top/anime"
    JIKAN_THEMES = "https://api.jikan.moe/v4/anime/{id}/themes"
    params = {
        "type": "tv",
        "filter": "bypopularity",
        "page": 1
    }
    # print("Fetching top anime pages...")
    all_anime = []
    if num >= 3:
        random_start = random.randint(1, num - 2)  # ensure room for +2
        random_end = random.randint(random_start + 2, num)
    else:
        random_start = 1
        random_end = num
    for page in range(random_start, random_end):  # fetch first 2 pages (adjust higher if needed)
        params['page'] = page
        try:
            data = fetch_jikan(JIKAN_TOP, params)['data']
        except:
            data = []
        all_anime.extend(data)
    # Filter for recent anime (from 2005 or newer)
    recent_anime = [
        anime for anime in all_anime 
        if 'year' in anime and anime['year'] is not None and anime['year'] >= 2005
    ]
    if not recent_anime:
        recent_anime = all_anime  # fallback if none meet criteria
    random_title = random.choice(recent_anime)
    name = random_title["titles"][0]["title"]
    id = random_title["mal_id"]
    # print("Selecting random openings...")
    oped_data = fetch_jikan(JIKAN_THEMES.format(id=id), {})['data']
    ops = oped_data.get("openings", [])
    eds = oped_data.get("endings", [])
    name = re.sub(r'[^\x00-\x7F]+', '', name)
    ops = [re.sub(r'\s*\(.*?\)\s*$', '', op).strip() for op in ops]
    print(f"Anime: {name}")
    return [name, {"Openings": ops, "Endings": eds}]

def get_multiple_random_themes(num_of_anime):
    collected = {}
    while len(collected) < num_of_anime:
        name, themes = get_random_title_themes()
        if name not in collected:
            collected[name] = themes
            print(f"✅ Added: {name}")
        else:
            print(f"⚠ Duplicate found: {name}, skipping...")

    return collected
def get_animes_by_keyword(keyword):
    results = []
    seen_ids = set()
    for anime_type in ["tv", "movie"]:
        params = {
            "type": anime_type,
            "q": keyword + " anime op"
        }
        data = fetch_jikan("https://api.jikan.moe/v4/anime", params)['data']
        for d in data:
            if d['mal_id'] not in seen_ids:
                results.append([d['mal_id'], d["title"]])
                seen_ids.add(d['mal_id'])
    return results

def get_openings_from_list(array):
    result = []
    JIKAN_THEMES = "https://api.jikan.moe/v4/anime/{id}/themes"
    for anime in array:
        id = anime[0]
        name = anime[1]
        oped_data = fetch_jikan(JIKAN_THEMES.format(id=id),{})['data']
        sleep(0.5)
        ops = oped_data["openings"]
        eds = oped_data["endings"]
        name = re.sub(r'[^\x00-\x7F]+', '', name)
        for i in range(len(ops)):
            ops[i] = re.sub(r'\s*\(.*?\)\s*$', '', ops[i]).strip()
            ops[i] = re.sub(r'^\d+[\.:] ', '', ops[i])
        result.append([name, {"Openings":ops,"Endings":eds}])
    return result