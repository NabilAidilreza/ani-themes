import os,sys,subprocess
import json
import random
import argparse
import pywintypes
import win32file
from time import sleep
from datetime import datetime,timedelta
from datetime import time as tm

# import importlib.resources

from utils import *
from rich_console import *
from jikan_client import get_animes_by_keyword,get_openings_from_list,get_random_title_themes
from yt_client import get_yt_link

#! JSON Files Setup #
try:
    config_manager = ConfigManager()
    config = config_manager.load()
except:
    config_template = {
    "ANI-THEMES-WINDOW-PLACEMENT": "top_right",
    "ANI-THEMES-HASJSON": "True",
    "ANI-THEMES-API-SEARCH-COUNT": 3,
    "ANI-THEMES-JSON-PLAYLIST-COUNT": 20,
    "YOUTUBE_API_KEY": "INSERT KEY HERE",
    "YOUTUBE_API_LIMIT_PER_DAY": 100,
    "YOUTUBE_API_CALL_COUNTER": 5,
    "LAST_API_RESET_DATE": "2025-07-30",
    "CURRENT-PLAYLIST": [],
    "CURRENT_INDEX": 0,
    "BLACKLISTED": []
    }
    with open("config.json", "w") as f:
        json.dump(config_template, f, indent=4)
    config_manager = ConfigManager()
    config = config_manager.load()

try:
    with open("saved_yt_links.json","r") as l:
        pass
except:
    links_template = {
    "videos": [] 
    }
    with open("saved_yt_links.json", "w") as f:
        json.dump(links_template, f, indent=4)

try:
    with open("progress.json","r") as l:
        pass
except:
    template = {
    }
    with open("progress.json", "w") as f:
        json.dump(template, f, indent=4)

#! API Reset Check #
now = datetime.now()
reset_time = tm(15, 0)  # 15:00
if now.time() >= reset_time:
    today_str = now.strftime("%Y-%m-%d")
else:
    today_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
if config.get("LAST_API_RESET_DATE") != today_str:
    warning("New day detected — resetting API counter to 0.")
    config["YOUTUBE_API_CALL_COUNTER"] = 0
    config["LAST_API_RESET_DATE"] = today_str
    config_manager.save(config)
        
#! Youtube Variables #
YOUTUBE_API_KEY = config['YOUTUBE_API_KEY']
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
LOCAL_MODE = config["ANI-THEMES-HASJSON"]

#! Control Pipes & Functions #
IPC_PIPE = r'\\.\pipe\mpvsocket'
CONTROLLER_PIPE = r'\\.\pipe\controllerpipe'

def send_command(handle, cmd):
    data = json.dumps(cmd) + "\n"
    win32file.WriteFile(handle, data.encode('utf-8'))
    dataout(f"Sent command to {handle}: {cmd}")

def connect_to_pipe(pipe_name, retries = 10):
    try:
        handle = win32file.CreateFile(
            pipe_name,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None, win32file.OPEN_EXISTING, 0, None
        )
        success(f"Connected to {pipe_name}")
        return handle
    except pywintypes.error as e:
        if e.winerror == 2:
            failure(f"Pipe {pipe_name} not found.")
            return None
        else:
            raise

def launch_controller():
    processing("Launching mpv_controller.py...")

    # controller_path = importlib.resources.files("ani_themes").joinpath("mpv_controller.py")
    subprocess.Popen(
        [sys.executable, "mpv_controller.py"],#str(controller_path)],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    # print(f"[*] Launched controller at {controller_path}")
    sleep(2)


def ensure_controller_running():
    mpv_handle = connect_to_pipe(IPC_PIPE)
    controller_handle = connect_to_pipe(CONTROLLER_PIPE)
    if mpv_handle is None or controller_handle is None:
        warning("Controller not detected. Launching...")
        launch_controller()
        mpv_handle = connect_to_pipe(IPC_PIPE, retries=10)
        controller_handle = connect_to_pipe(CONTROLLER_PIPE, retries=10)
        if controller_handle:
            finalok("Controller is live and responsive.")
        else:
            failure("Controller is not responding. Attempting restart...")
            launch_controller()
        if mpv_handle is None or controller_handle is None:
            fatal("Failed to connect after launching controller.")
            sys.exit(1)
    return mpv_handle, controller_handle




#! Main Loop #
def main():
    global LOCAL_MODE
    parser = argparse.ArgumentParser(
        description="ani-themes: CLI to play anime openings"
    )
    parser.add_argument("-p", action="store_true", help="Launch playlist mode.")
    parser.add_argument("-s", action="store_true", help="Search openings by anime.")
    parser.add_argument("-r", action="store_true", help="Play a random anime opening.")
    args = parser.parse_args()
    mpv_handle, controller_handle = None, None
    def check_archive_if_no_link(yt_link,opening):
        if yt_link == "" and os.path.exists("saved_yt_links.json"):
            with open("saved_yt_links.json", "r", encoding="utf-8") as f:
                parsed = json.load(f)
                return next((v['url'] for v in parsed['videos'] if opening in v['title']), "")
        else:
            return yt_link
    def playlist_mode(mpv_handle = None, controller_handle = None):
        ### Send Start Signal ###
        if mpv_handle is None or controller_handle is None:
            mpv_handle, controller_handle = ensure_controller_running()
        send_command(controller_handle, {
            "command": "loadplaylist",
            "data": {"has_json": LOCAL_MODE}
        })
        user("+--------------------------------+")
        user("| 🎵 Loading playlist...         |")
        user("| This may take a while...       |")
        user("| Upon completion, auto restart  |")
        user("| This may take a few seconds... |")
        user("+--------------------------------+")
        ### Loading Portion ###
        progress_info = {
            "status": "Initializing...",
            "song_name": "",
            "song_link": ""
        }
        write_progress(progress_info)
        display_progress()
        ### Controls ###
        while True:
            options = ["Next","Replay","Previous","View Current Playlist", "Exit"]
            user_input = multi_prompt(options,"ani-themes")
            if user_input == "Next":
                user("If it’s taking a bit, the player might be refreshing the playlist...")
                send_command(controller_handle, {"command": "next"})
            elif user_input == "Replay":
                send_command(controller_handle, {"command": "replay"})
            elif user_input == "Previous":
                send_command(controller_handle, {"command": "prev"})
            elif user_input == "View Current Playlist":
                config_manager = ConfigManager()
                config = config_manager.load()
                curr_playlist = config['CURRENT-PLAYLIST']
                curr_index = config['CURRENT_INDEX'] 
                curr_playlist.append("Back")
                view_playlist = multi_prompt(curr_playlist,"ani-themes",curr_index)
            elif user_input == "Exit":
                send_command(controller_handle, {"command": "quit"})
                break
    def search_mode(mpv_handle = None, controller_handle = None,enterFlag = False):
        anime_keyword = input("Search anime: ")
        if anime_keyword:
            loading_anim,anim_thread = datain_anim("Fetching data")
            with time_check() as tc:
                results = get_openings_from_list(get_animes_by_keyword(anime_keyword))
                loading_anim.set() # Stop animation
                anim_thread.join()
            datain("Fetching data...")
            print(f" [✅ took {tc['elapsed']:.2f}s]")
            anime = [r[0] for r in results]
            openings = [r[1]["Openings"] for r in results]
            which_anime = multi_prompt(anime, "Anime Search")
            chosen = anime.index(which_anime)
            cleaned_openings = [o.replace('"', '') for o in openings[chosen]]
            opening = (multi_prompt(cleaned_openings, "Openings")
                    if len(cleaned_openings) > 1 else cleaned_openings[0])
            yt_link,song_title,save_msg = get_yt_link(which_anime, opening, YOUTUBE_API_KEY, YOUTUBE_SEARCH_URL)
            yt_link = check_archive_if_no_link(yt_link,opening)
            if mpv_handle is None or controller_handle is None:
                mpv_handle, controller_handle = ensure_controller_running()
            if enterFlag == False:
                send_command(controller_handle, {
                    "command": "loadsingle",
                    "data": {"url": yt_link}
                })
                music(song_title,context=save_msg,status="Now Playing")
            else:
                send_command(controller_handle, {
                    "command": "loadsingle_queue",
                    "data": {"url": yt_link}
                })
                music(song_title,context=save_msg,status="Added to Queue")
            mpv_player(which_anime, anime, openings, yt_link,mpv_handle,controller_handle)
    def mpv_player(anime_title,animes,openings,yt_link,mpv_handle,controller_handle):
        main_title = get_main_title(anime_title)
        while True:
            user_input = multi_prompt([f"{main_title} OPs", "Replay","Look Up Another Anime", "Exit"], "ani-themes")
            if user_input == f"{main_title} OPs":
                s_ops = [
                    o.replace('"', '')
                    for i, anime in enumerate(animes)
                    if main_title in anime
                    for o in openings[i]
                ]
                opening = multi_prompt(s_ops,f"{main_title}")
                play_or_queue = multi_prompt(['Play','Add to queue','Back'],"Song Options")
                yt_link,song_title,save_msg = get_yt_link(anime_title,opening,YOUTUBE_API_KEY,YOUTUBE_SEARCH_URL)
                yt_link = check_archive_if_no_link(yt_link,opening)
                if play_or_queue == 'Play':
                    music(song_title,context=save_msg,status="Now Playing")
                    send_command(controller_handle, {"command": "loadsingle", "data": {"url": yt_link}})
                elif play_or_queue == 'Add to queue':
                    music(song_title,context=save_msg,status="Added to Queue")
                    send_command(controller_handle, {"command": "loadsingle_queue", "data": {"url": yt_link}})
                else:
                    continue
            elif user_input == "Replay":
                send_command(controller_handle, {"command": "replay"})
            elif user_input == "Look Up Another Anime":
                return search_mode(mpv_handle,controller_handle,True)
            elif user_input == "Exit":
                warning("Exiting mpv player loop.")
                send_command(controller_handle, {"command": "quit"})
                break
            sleep(0.2)
    def random_mode(mpv_handle = None, controller_handle = None):
        if mpv_handle is None or controller_handle is None:
            mpv_handle, controller_handle = ensure_controller_running()
        anime_data = get_random_title_themes()
        anime_title = anime_data[0]
        openings = anime_data[1]["Openings"]
        opening = random.choice(openings)
        yt_link,song_title,save_msg = get_yt_link(anime_title,opening,YOUTUBE_API_KEY,YOUTUBE_SEARCH_URL)
        yt_link = check_archive_if_no_link(yt_link,opening)
        send_command(controller_handle, {
            "command": "loadsingle",
            "data": {"url": yt_link}
        })
    def edit_config():
        user_input = multi_prompt(["Change MPV Placement","Set API Key","Check API Stats","Blacklist Menu","Exit"],"Configs")
        if user_input == "Change MPV Placement":
            config = config_manager.load()
            curr_win_plac = config["ANI-THEMES-WINDOW-PLACEMENT"]
            change_window = multi_prompt(['top_left','top_right','bottom_left','bottom_right','center'],f"Current Placement: {curr_win_plac}")
            config["ANI-THEMES-WINDOW-PLACEMENT"] = change_window
            config_manager.save(config)
        elif user_input == "Set API Key":
            config = config_manager.load()
            change_api_key = input("New API Key: ")
            config["YOUTUBE_API_KEY"] = change_api_key
            config_manager.save(config)
        elif user_input == "Check API Stats":
            config = config_manager.load()
            api_key = config.get("YOUTUBE_API_KEY", 0)
            api_limit = config.get("YOUTUBE_API_LIMIT_PER_DAY", 0)
            api_counter = config.get("YOUTUBE_API_CALL_COUNTER", 0)
            remaining = api_limit - api_counter
            user("\n=== YouTube API Stats ===")
            user(f"API Key: {api_key if api_key else '(empty)'}")
            user(f"Daily Limit: {api_limit}")
            user(f"Calls Used Today: {api_counter}")
            user(f"Remaining Calls Today: {remaining if remaining >= 0 else 0}")
            user("==========================\n")
        elif user_input == "Blacklist Menu":
            while True:
                user_input = multi_prompt(["View Blacklist","Edit Blacklist","Add to Blacklist","Back"],"Menu")
                config = config_manager.load()
                curr_blacklist = config["BLACKLISTED"]
                if user_input == "View Blacklist":
                    for anime in curr_blacklist:
                        print(anime)
                elif user_input == "Edit Blacklist":
                    user_input = multi_prompt(curr_blacklist,"Edit")
                    options = multi_prompt(["Remove","Back"],"Option")
                    if options == "Remove":
                        curr_blacklist.remove(user_input)
                        config["BLACKLISTED"] = curr_blacklist
                        config_manager.save(config)
                elif user_input == "Add to Blacklist":
                    user_input = multi_prompt(load_all_unique_titles(),"Edit")
                    options = multi_prompt(["Add","Back"],"Option")
                    if options == "Add":
                        curr_blacklist.append(user_input)
                        config["BLACKLISTED"] = curr_blacklist
                        config_manager.save(config)
                else:
                    break
    try:
        if len(sys.argv) == 1:
            options = ["Search Anime Opening", "Player","Config"]
            user_input = multi_prompt(options,"ani-themes")
            if user_input == "Search Anime Opening":
                search_mode()
            elif user_input == "Player":
                playlist_mode()
            elif user_input == "Config":
                edit_config()
                main()
        if args.p:
            playlist_mode()
        elif args.s:
            search_mode()
        elif args.r:
            random_mode()
    finally:
        if mpv_handle:
            warning("Closing mpv_handle")
            win32file.CloseHandle(mpv_handle)
        if controller_handle:
            warning("Closing controller_handle")
            win32file.CloseHandle(controller_handle)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        warning("Exiting cleanly...")
    