import os,sys
import json
import argparse
import win32file
from time import sleep
from datetime import datetime,timedelta
from datetime import time as tm

# import importlib.resources

from utils import ConfigManager, multi_prompt, AnimeVideoManager
from rich_console import *
from cli import search_mode,playlist_mode,random_mode,edit_config,shutdown_and_verify_pipes

#! JSON Files and Settings Setup #
def ensure_config_file(filepath,default_content):
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default_content, f, indent=4)
    config_manager = ConfigManager()
    return config_manager.load()
    
def ensure_json_file(filepath, default_content):
    """Ensure a JSON file exists with default content if missing or invalid."""
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default_content, f, indent=4)
    else:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                json.load(f)  # Attempt to parse it to ensure it's valid JSON
        except (json.JSONDecodeError, IOError):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(default_content, f, indent=4)

def setup_environment():
    config_template = {
    "ANI-THEMES-WINDOW-PLACEMENT": "top_right",
    "ANI-THEMES-HASJSON": "True",
    "ANI-THEMES-API-SEARCH-COUNT": 3,
    "ANI-THEMES-JSON-PLAYLIST-COUNT": 10,
    "YOUTUBE_API_KEY": "INSERT KEY HERE",
    "YOUTUBE_API_LIMIT_PER_DAY": 100,
    "YOUTUBE_API_CALL_COUNTER": 5,
    "LAST_API_RESET_DATE": "2025-07-30",
    "CURRENT-PLAYLIST": [],
    "CURRENT_INDEX": 0,
    "BLACKLISTED": []
    }
    config_manager = ConfigManager()
    config = ensure_config_file("config.json",config_template)
    config["CURRENT_INDEX"] = 0
    config_manager.save(config)
    ensure_json_file("saved_yt_links.json", {"videos": []})
    ensure_json_file("progress.json", {})

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

def display_banner():
    banner = """
════════════ 🎵 ANI-THEMES 🎵 ════════════
           Anime Theme Player    
          ─────────────────────
          ♫ By CamkoalatiXD ♫    
    """
    print(banner)

#! Main Loop #
def main():
    setup_environment()

    #? CLI Setup #
    parser = argparse.ArgumentParser(
        description="ani-themes: CLI to play anime openings"
    )
    parser.add_argument("-p", action="store_true", help="Launch playlist mode.")
    parser.add_argument("-s", action="store_true", help="Search openings by anime.")
    parser.add_argument("-r", action="store_true", help="Play a random anime opening.")
    args = parser.parse_args()

    try:
        if len(sys.argv) == 1:
            #display_banner()
            options = ["Search Anime Opening", "Player","Settings"]
            user_input = multi_prompt(options,"ani-themes")
            if user_input:
                if user_input == "Search Anime Opening":
                    search_mode()
                elif user_input == "Player":
                    playlist_mode()
                elif user_input == "Settings":
                    edit_config()
                    main()
        if args.p:
            playlist_mode()
        elif args.s:
            search_mode()
        elif args.r:
            random_mode()
    finally:
        shutdown_and_verify_pipes()
        warning("Closing program in 2s...")
        sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        warning("Exiting cleanly...")
    