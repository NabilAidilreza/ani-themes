import re
import requests
import random
from time import sleep
import httpx
import asyncio


def fetch_jikan(api,params):
    try:
        return requests.get(api, params=params).json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except ValueError as e:
        print(f"JSON decoding failed: {e}")
        return None
    
def get_random_title_themes(num = 5, page_span = 3):
    JIKAN_TOP = "https://api.jikan.moe/v4/top/anime"
    JIKAN_THEMES = "https://api.jikan.moe/v4/anime/{id}/themes"
    # print("Fetching top anime pages...")
    # Pick a random start page (ensure at least page_span pages available)
    max_start_page = max(1, 10 - (page_span - 1))  # Avoid going past page 10
    start_page = random.randint(1, max_start_page)
    pages = range(start_page, start_page + page_span)
    
    all_anime = []
    
    for page in pages:
        params = {
            "type": "tv",
            "filter": "bypopularity",
            "page": page
        }
        try:
            response = fetch_jikan(JIKAN_TOP, params)
            data = response.get("data", [])
            all_anime.extend(data)
            sleep(1)
        except Exception as e:
            print(f"[!] Failed to fetch page {page}: {e}")
    # Filter for recent anime (from 2005 or newer)
    recent_anime = [
        anime for anime in all_anime 
        if 'year' in anime and anime['year'] is not None and anime['year'] >= 2005
    ] or all_anime
    random_title = random.choice(recent_anime)
    name = random_title["titles"][0]["title"]
    id = random_title["mal_id"]
    # print("Selecting random openings...")
    # Need to fix rate limit and handle null values
    # YT API Counter not correct need fix
    oped_data = fetch_jikan(JIKAN_THEMES.format(id=id), {})["data"]
    ops = oped_data.get("openings", [])
    eds = oped_data.get("endings", [])
    name = re.sub(r'[^\x00-\x7F]+', '', name)
    ops = [re.sub(r'\s*\(.*?\)\s*$', '', op).strip() for op in ops]
    return [name, {"Openings": ops, "Endings": eds}]

async def fetch_jikan_async(client, params):
    try:
        resp = await client.get("https://api.jikan.moe/v4/anime", params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None
    
async def get_animes_by_keyword(keyword, max_results=10):
    seen_ids = set()
    params_list = [
        {"q": keyword, "type": t, "limit": max_results, "fields": "mal_id,title", "order_by": "popularity", "sort": "asc"}
        for t in ("tv", "movie")
    ]

    async with httpx.AsyncClient() as client:
        results = []
        for d in (item for resp in await asyncio.gather(*(fetch_jikan_async(client, p) for p in params_list))
                  for item in resp.get("data", []) if item["mal_id"] not in seen_ids):
            results.append([d["mal_id"], d["title"]])
            seen_ids.add(d["mal_id"])
            if len(results) >= max_results:
                break
    return results

# def get_animes_by_keyword(keyword, max_results=20):
#     results = []
#     seen_ids = set()
    
#     # Add 'limit' and better query
#     for anime_type in ["tv", "movie"]:
#         params = {
#             "q": keyword,
#             "type": anime_type,
#             "limit": max_results,  # Jikan supports this
#             "order_by": "popularity",  # or "score", "favorites"
#             "sort": "asc"  # or "desc"
#         }
#         response = fetch_jikan("https://api.jikan.moe/v4/anime", params)
#         if not response or 'data' not in response:
#             continue
#         for d in response['data']:
#             if d['mal_id'] not in seen_ids:
#                 results.append([d['mal_id'], d["title"]])
#                 seen_ids.add(d['mal_id'])
#                 if len(results) >= max_results:
#                     return results  # Return early if enough
#     return results

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