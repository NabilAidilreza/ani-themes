import os,sys,subprocess
import json
import asyncio
import random
import pywintypes
import win32file
import psutil
from time import sleep

from utils import *
from rich_console import *
from jikan_client import get_animes_by_keyword,get_openings_from_list,get_random_title_themes,get_songs_from_anime_name
from yt_client import get_yt_link

#! Youtube Variables #
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
config = ConfigManager().load()
debug_switch = config["DEBUG"]

#! Pipe Functions #
def send_command(handle, cmd):
    global debug_switch
    data = json.dumps(cmd) + "\n"
    win32file.WriteFile(handle, data.encode('utf-8'))
    if debug_switch != "False":
        dataout(f"Sent command to {handle}: {cmd}")

def connect_to_pipe(pipe_name):
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

def check_all_pipes_closed(verbose=True, return_details=False):
    PIPE_NAMES = [r'\\.\pipe\mpvsocket', r'\\.\pipe\controllerpipe']
    pipe_statuses = {}

    for pipe in PIPE_NAMES:
        try:
            handle = win32file.CreateFile(
                pipe,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )
            pipe_statuses[pipe] = "open"
            if verbose:
                warning(f"Pipe {pipe} is still open.")
            win32file.CloseHandle(handle)
        except pywintypes.error as e:
            if e.winerror == 2:
                pipe_statuses[pipe] = "closed"
                if verbose:
                    success(f"Pipe {pipe} is closed or does not exist.")
            elif e.winerror == 231:
                pipe_statuses[pipe] = "busy"
                if verbose:
                    warning(f"Pipe {pipe} exists but is busy (likely still open).")
            else:
                pipe_statuses[pipe] = f"error: {str(e)}"
                if verbose:
                    failure(f"Error checking {pipe}: {e}")

    all_closed = all(status == "closed" for status in pipe_statuses.values())

    if not all_closed and verbose:
        warning(f"Detected open/busy pipe(s): {', '.join([k for k,v in pipe_statuses.items() if v != 'closed'])}")
    elif verbose:
        finalok("All pipes are cleanly closed.")

    return pipe_statuses if return_details else all_closed

def shutdown_and_verify_pipes(max_retries=5, delay=2):
    processing("Waiting for controller to exit and pipes to close...")

    for attempt in range(max_retries):
        statuses = check_all_pipes_closed(verbose=True, return_details=True)
        if all(status == "closed" for status in statuses.values()):
            finalok("Clean shutdown confirmed.")
            return True
        else:
            warning(f"[Attempt {attempt + 1}/{max_retries}] Pipes still not closed. Retrying in {delay}s...")
            sleep(delay)

    fatal("Some pipes remained open/busy after max retries.")
    user("Pipe Statuses:")
    for pipe, status in statuses.items():
        user(f" - {pipe}: {status}")
    return False

#! Controller Functions #
def launch_controller():
    processing("Launching mpv_controller.py...")
    # controller_path = importlib.resources.files("ani_themes").joinpath("mpv_controller.py")
    subprocess.Popen(
        [sys.executable, "mpv_controller.py"],#str(controller_path)],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    sleep(2)

def ensure_controller_running():
    #! Control Pipes #
    IPC_PIPE = r'\\.\pipe\mpvsocket'
    CONTROLLER_PIPE = r'\\.\pipe\controllerpipe'

    mpv_handle = connect_to_pipe(IPC_PIPE)
    controller_handle = connect_to_pipe(CONTROLLER_PIPE)
    if mpv_handle is None or controller_handle is None:
        warning("Controller not detected. Launching...")
        launch_controller()
        mpv_handle = connect_to_pipe(IPC_PIPE)
        controller_handle = connect_to_pipe(CONTROLLER_PIPE)
        if controller_handle:
            finalok("Controller is live and responsive.")
        else:
            failure("Controller is not responding. Attempting restart...")
            launch_controller()
        if mpv_handle is None or controller_handle is None:
            fatal("Failed to connect after launching controller.")
            sys.exit(1)
    return mpv_handle, controller_handle

def get_cached_link(search_value, match_field="title"):
    """Return (url, title) from cache if found, else (None, None)."""
    if os.path.exists("resources/saved_yt_links.json"):
        with open("resources/saved_yt_links.json", "r", encoding="utf-8") as f:
            parsed = json.load(f)
            for v in parsed.get('videos', []):
                if search_value in v.get(match_field, ""):
                    return v.get("url"), v.get("title")
    return None, None
    
def is_player_ui_running(script_name="player_ui.py") -> bool:
    """Check if player_ui.py is already running."""
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and script_name in ' '.join(cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def spawn_player_ui():
    """Spawn player_ui.py in a new terminal if not already running."""
    if not is_player_ui_running():
        processing("Spawning playlist tracker...")
        subprocess.Popen(
            ["cmd", "/c", "start", "cmd", "/k", "python player_ui.py"],
            shell=True
        )

def kill_player_ui_by_name(script_name="player_ui.py"):
    """Kill all processes running player_ui.py."""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['cmdline'] and script_name in ' '.join(proc.info['cmdline']):
                print(f"Killing: {proc.pid} {proc.info['cmdline']}")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def playlist_mode(mpv_handle = None, controller_handle = None):
    if mpv_handle is None or controller_handle is None:
        mpv_handle, controller_handle = ensure_controller_running()
    config = ConfigManager().load()
    LOCAL_MODE = config["ANI-THEMES-HASJSON"]
    send_command(controller_handle, {
        "command": "loadplaylist",
        "data": {"has_json": LOCAL_MODE}
    })

    music("Loading playlist...")
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
            send_command(controller_handle, {"command": "next"})
        elif user_input == "Replay":
            send_command(controller_handle, {"command": "replay"})
        elif user_input == "Previous":
            send_command(controller_handle, {"command": "prev"})
        elif user_input == "View Current Playlist":
            spawn_player_ui()
        elif user_input == "Exit":
            send_command(controller_handle, {"command": "quit"})
            kill_player_ui_by_name()
            break
def search_mode(mpv_handle = None, controller_handle = None,enterFlag = False):
    config_manager = ConfigManager()
    YOUTUBE_API_KEY = config_manager.load()['YOUTUBE_API_KEY']
    anime_keyword = question("Search anime: ")
    if anime_keyword:
        results = run_with_animation(
            lambda: get_openings_from_list(asyncio.run(get_animes_by_keyword(anime_keyword))),
            text="Fetching data",
            text_type="datain"
        )
        anime = [r[0] for r in results]
        openings = [r[1]["Openings"] for r in results]
        endings =  [r[1]["Endings"] for r in results]
        which_anime = multi_prompt(anime, "Anime available")
        chosen = anime.index(which_anime)

        # cleaned_openings = [o.replace('"', '') for o in openings[chosen]]
        # cleaned_endings = [o.replace('"', '') for o in endings[chosen]]

        cleaned_openings, cleaned_endings = (
            [o.replace('"', '') for o in seq] 
            for seq in (openings[chosen], endings[chosen])
        )
        cleaned_all = cleaned_openings + cleaned_endings

        if len(cleaned_all) == 0:
            fatal("No songs available!")
            return search_mode()
        else:
            music("Available Songs",status="Loaded")
        opening = (multi_prompt(cleaned_all, "OPs|EDs")
                if len(cleaned_all) > 1 else cleaned_all[0])
        cached_link, song_title = get_cached_link(opening)
        if cached_link:
            yt_link = cached_link
            save_msg = "[Using Cached Link]"
        else:
            yt_link,song_title,save_msg = get_yt_link(which_anime, opening, YOUTUBE_API_KEY, YOUTUBE_SEARCH_URL)
        if yt_link:
            add_search(which_anime + ": " + opening)
            if mpv_handle is None or controller_handle is None:
                mpv_handle, controller_handle = ensure_controller_running()
            if not enterFlag:
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
        mpv_player(which_anime, anime, openings,endings, yt_link,mpv_handle,controller_handle,YOUTUBE_API_KEY)

def search_exact_mode(mpv_handle = None, controller_handle = None,enterFlag = False):
    config_manager = ConfigManager()
    YOUTUBE_API_KEY = config_manager.load()['YOUTUBE_API_KEY']
    anime_keyword = question("Search exact anime: ")
    if anime_keyword:
        result = run_with_animation_sync(
            get_songs_from_anime_name,
            anime_keyword,
            text="Fetching data",
            text_type="datain"
        )
        anime_title = result["Title"]
        openings = result["Openings"]
        endings =  result["Endings"]
        songs = openings + endings
        chosen_song = (multi_prompt(songs, "OPs|EDs")
                if len(songs) > 1 else songs[0])
        cached_link, song_title = get_cached_link(chosen_song)
        if cached_link:
            yt_link = cached_link
            save_msg = "[Using Cached Link]"
        else:
            yt_link,song_title,save_msg = get_yt_link(anime_title, chosen_song, YOUTUBE_API_KEY, YOUTUBE_SEARCH_URL)
        if yt_link:
            add_search(anime_title + ": " + chosen_song)
            if mpv_handle is None or controller_handle is None:
                mpv_handle, controller_handle = ensure_controller_running()
            if not enterFlag:
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
        search_exact_mode(mpv_handle,controller_handle,True)


def mpv_player(anime_title,animes,openings,endings, yt_link,mpv_handle,controller_handle,YOUTUBE_API_KEY):
    main_title = get_main_title(anime_title)
    while True:
        user_input = multi_prompt([f"{main_title} OPs",f"{main_title} EDs", "Replay","Look Up Another Anime", "Exit"], "ani-themes")
        if main_title in user_input:
            check_which_type = user_input.split(" ")[-1]
            source_list = openings if check_which_type == "OPs" else endings
            source_songs = [
                o.replace('"', '')
                for i, anime in enumerate(animes)
                if main_title in anime
                for o in source_list[i]
            ]
            source_songs.append("Back")
            selected_song = multi_prompt(source_songs,f"{main_title}")
            if selected_song == "Back": continue
            play_or_queue = multi_prompt(['Play','Add to queue','Back'],"Song Options")
            cached_link, song_title = get_cached_link(selected_song)
            if cached_link:
                yt_link = cached_link
                save_msg = "[Using Cached Link]"
            else:
                yt_link,song_title,save_msg = get_yt_link(anime_title, selected_song, YOUTUBE_API_KEY, YOUTUBE_SEARCH_URL)
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
            return search_mode(mpv_handle,controller_handle,True,)
        elif user_input == "Exit":
            warning("Exiting mpv player loop.")
            send_command(controller_handle, {"command": "quit"})
            break
        sleep(0.2)
def random_mode(mpv_handle = None, controller_handle = None):
    if mpv_handle is None or controller_handle is None:
        mpv_handle, controller_handle = ensure_controller_running()
    config_manager = ConfigManager()
    YOUTUBE_API_KEY = config_manager.load()['YOUTUBE_API_KEY']
    anime_data = get_random_title_themes()
    anime_title = anime_data[0]
    openings = anime_data[1]["Openings"]
    opening = random.choice(openings)
    cached_link, song_title = get_cached_link(opening)
    if cached_link:
        yt_link = cached_link
        save_msg = "[Using Cached Link]"
    else:
        yt_link,song_title,save_msg = get_yt_link(anime_title, opening, YOUTUBE_API_KEY, YOUTUBE_SEARCH_URL)
    send_command(controller_handle, {
        "command": "loadsingle",
        "data": {"url": yt_link}
    })
def edit_config():
    config_manager = ConfigManager()
    user_input = multi_prompt(["Toggle Local Mode","Change MPV Placement","Set API Key","Check API Stats","Blacklist Menu","Manage Cached Links","Exit"],"Settings")
    if user_input == "Toggle Local Mode":
        config = config_manager.load()
        options = multi_prompt(['Yes','No'],"Use locally? (Use cached links / no api calls)")
        config["ANI-THEMES-HASJSON"] = "True" if options == "Yes" else "False"
        config_manager.save(config)
    elif user_input == "Change MPV Placement":
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
    elif user_input == "Manage Cached Links":
        manager = AnimeVideoManager("resources/saved_yt_links.json")
        manager.remove_duplicates()
        manager.sort_by_anime()
        manager.save()
        while True:
            user_input = multi_prompt(["View All Unique Anime Series","Remove Anime Series","Back"],"Menu")
            if user_input == "View All Unique Anime Series":
                anime_name = multi_prompt(manager.view_unique_anime_names(),"Animes")
            elif user_input == "Remove Anime Series":
                num = question("How many series? (default is 1): ")
                if num == "" or num.isnumeric() == False:
                    num = 1
                num = int(num)
                while num > 0:
                    anime_name = multi_prompt(manager.view_unique_anime_names(),"Animes")
                    manager.delete_by_anime_name(anime_name)
                    manager.save()
                    num -= 1

            else:
                break