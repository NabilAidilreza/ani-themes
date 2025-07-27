import os,sys,subprocess
import json
import random
import argparse
import pywintypes
import win32file
import win32pipe
import logging
from time import sleep
from datetime import datetime, time,timedelta
# import importlib.resources

from jikan_fetcher import get_animes_by_keyword,get_openings_from_list,get_random_title_themes
from yt_finder import get_yt_link
from helper_functions import *

#! OS Check #
if os.name != 'nt':
    logging.info("This script runs only on Windows.")
    sys.exit(1)

#! Logging Setup #
# Setup logging format and level
logging.basicConfig(
    level=logging.INFO,  # change to DEBUG for detailed logs
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

#! Config Setup #
config_manager = ConfigManager()
config = config_manager.load()

#! API Reset Check #
now = datetime.now()
reset_time = time(15, 0)  # 15:00
if now.time() >= reset_time:
    today_str = now.strftime("%Y-%m-%d")
else:
    today_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
if config.get("LAST_API_RESET_DATE") != today_str:
    logging.info("New day detected — resetting API counter to 0.")
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
    logging.info(f"[>] Sent command to {handle}: {cmd}")

def connect_to_pipe(pipe_name, retries=10, delay=0.5):
    try:
        handle = win32file.CreateFile(
            pipe_name,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None, win32file.OPEN_EXISTING, 0, None
        )
        logging.info(f"[*] Connected to {pipe_name}")
        return handle
    except pywintypes.error as e:
        if e.winerror == 2:
            logging.warning(f"[!] Pipe {pipe_name} not found.")
            return None
        else:
            raise

def launch_controller():
    logging.info("[*] Launching mpv_controller.py...")

    # controller_path = importlib.resources.files("ani_themes").joinpath("mpv_controller.py")
    subprocess.Popen(
        [sys.executable, "mpv_controller.py"],#str(controller_path)],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    # logging.info(f"[*] Launched controller at {controller_path}")
    sleep(2)


def ensure_controller_running():
    mpv_handle = connect_to_pipe(IPC_PIPE)
    controller_handle = connect_to_pipe(CONTROLLER_PIPE)
    if mpv_handle is None or controller_handle is None:
        logging.info("[*] Controller not detected. Launching...")
        launch_controller()
        mpv_handle = connect_to_pipe(IPC_PIPE, retries=10)
        controller_handle = connect_to_pipe(CONTROLLER_PIPE, retries=10)
        if controller_handle:
            logging.info("Controller is live and responsive.")
        else:
            logging.warning("Controller is not responding. Attempting restart...")
            launch_controller()
        if mpv_handle is None or controller_handle is None:
            logging.error("[ERROR] Failed to connect after launching controller.")
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
    def playlist_mode():
        mpv_handle, controller_handle = ensure_controller_running()
        send_command(controller_handle, {
            "command": "loadplaylist",
            "data": {"has_json": LOCAL_MODE}
        })

        logging.info("+--------------------------------+")
        logging.info("| 🎵 Loading playlist...         |")
        logging.info("| This may take a while...       |")
        logging.info("| Upon completion, auto restart  |")
        logging.info("| This may take a few seconds... |")
        logging.info("+--------------------------------+")
        while True:
            options = ["Next","Replay","Previous","View Current Playlist", "Exit"]
            user_input = multi_prompt(options,"ani-themes")
            if user_input == "Next":
                print("If it’s taking a bit, the player might be refreshing the playlist...")
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
    def search_mode():
        anime_keyword = input("Search anime: ")
        if anime_keyword:
            logging.info("[*] Fetching data...")
            results = get_openings_from_list(get_animes_by_keyword(anime_keyword))
            anime = [r[0] for r in results]
            openings = [r[1]["Openings"] for r in results]
            which_anime = multi_prompt(anime, "Anime Search")
            chosen = anime.index(which_anime)
            cleaned_openings = [o.replace('"', '') for o in openings[chosen]]
            opening = (multi_prompt(cleaned_openings, "Openings")
                    if len(cleaned_openings) > 1 else cleaned_openings[0])
            yt_link = get_yt_link(which_anime, opening, YOUTUBE_API_KEY, YOUTUBE_SEARCH_URL)
            if yt_link == "" and os.path.exists("yt_anithemes_links.json"):
                with open("yt_anithemes_links.json", "r", encoding="utf-8") as f:
                    parsed = json.load(f)
                    yt_link = next((v['url'] for v in parsed['videos'] if opening in v['title']), "")
            mpv_handle, controller_handle = ensure_controller_running()
            send_command(controller_handle, {
                "command": "loadsingle",
                "data": {"url": yt_link}
            })
            mpv_player(which_anime, anime, openings, yt_link,mpv_handle,controller_handle)
    def mpv_player(anime_title,animes,openings,yt_link,mpv_handle,controller_handle):
        main_title = get_main_title(anime_title)
        while True:
            user_input = multi_prompt([f"{main_title} OPs", "Replay", "Exit"], "ani-themes")
            if user_input == f"{main_title} OPs":
                s_ops = [
                    o.replace('"', '')
                    for i, anime in enumerate(animes)
                    if main_title in anime
                    for o in openings[i]
                ]
                opening = multi_prompt(s_ops,f"{main_title}")
                play_or_queue = multi_prompt(['Play','Add to queue','Back'],"Song Options")
                if play_or_queue == 'Play':
                    yt_link = get_yt_link(anime_title,opening,YOUTUBE_API_KEY,YOUTUBE_SEARCH_URL)
                    if yt_link == "" and os.path.exists("yt_anithemes_links.json"):
                        with open("yt_anithemes_links.json", "r", encoding="utf-8") as f:
                            parsed = json.load(f)
                            yt_link = next((v['url'] for v in parsed['videos'] if opening in v['title']), "")
                    send_command(controller_handle, {"command": "loadsingle", "data": {"url": yt_link}})
                elif play_or_queue == 'Add to queue':
                    yt_link = get_yt_link(anime_title,opening,YOUTUBE_API_KEY,YOUTUBE_SEARCH_URL)
                    if yt_link == "" and os.path.exists("yt_anithemes_links.json"):
                        with open("yt_anithemes_links.json", "r", encoding="utf-8") as f:
                            parsed = json.load(f)
                            yt_link = next((v['url'] for v in parsed['videos'] if opening in v['title']), "")
                    send_command(controller_handle, {"command": "loadsingle_queue", "data": {"url": yt_link}})
                else:
                    continue
            elif user_input == "Replay":
                send_command(controller_handle, {"command": "replay"})
            elif user_input == "Exit":
                logging.info("[*] Exiting mpv player loop.")
                send_command(controller_handle, {"command": "quit"})
                break
            sleep(0.2)
    def random_mode():
        mpv_handle, controller_handle = ensure_controller_running()
        anime_data = get_random_title_themes()
        anime_title = anime_data[0]
        openings = anime_data[1]["Openings"]
        opening = random.choice(openings)
        yt_link = get_yt_link(anime_title,opening,YOUTUBE_API_KEY,YOUTUBE_SEARCH_URL)
        if yt_link == "" and os.path.exists("yt_anithemes_links.json"):
            with open("yt_anithemes_links.json", "r", encoding="utf-8") as f:
                parsed = json.load(f)
                yt_link = next((v['url'] for v in parsed['videos'] if opening in v['title']), "")
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
            logging.info("\n=== YouTube API Stats ===")
            logging.info(f"API Key: {api_key if api_key else '(empty)'}")
            logging.info(f"Daily Limit: {api_limit}")
            logging.info(f"Calls Used Today: {api_counter}")
            logging.info(f"Remaining Calls Today: {remaining if remaining >= 0 else 0}")
            logging.info("==========================\n")
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
        if args.p:
            playlist_mode()
        elif args.s:
            search_mode()
        elif args.r:
            random_mode()
    finally:
        if mpv_handle:
            logging.info("[*] Closing mpv_handle")
            win32file.CloseHandle(mpv_handle)
        if controller_handle:
            logging.info("[*] Closing controller_handle")
            win32file.CloseHandle(controller_handle)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Exiting cleanly...")
    