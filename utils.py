import os
import re
import json
# import importlib.resources
import tempfile
from time import sleep,time
from rich.live import Live
from rich.console import Group
from rich.spinner import Spinner
from rich.panel import Panel
from InquirerPy import prompt

from rich.console import Console
from rich.table import Table

class ConfigManager:
    def __init__(self,path = "config.json"):
        # self.path = importlib.resources.files("ani_themes") / "config.json"
        self.path = path
    def load(self):
        # config_path = importlib.resources.files("ani_themes") / "config.json"
        # with config_path.open("r", encoding="utf-8") as f:
        #     self.data = json.load(f)
        with open(self.path,encoding='utf-8') as f:
            self.data = json.load(f)
        return self.data
    def save(self,newdata):
        with open(self.path, 'w') as f:
            json.dump(newdata, f, indent=2)

class AnimeVideoManager:
    def __init__(self, file_path):
        """Initialize by loading data from a JSON file."""
        self.file_path = file_path
        with open(file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def sort_by_anime(self):
        """Sorts the videos by anime name alphabetically."""
        self.data['videos'] = sorted(self.data['videos'], key=lambda x: x['anime'])

    def remove_duplicates(self):
        """Removes duplicate entries from the videos list."""
        seen = set()
        unique_videos = []
        for video in self.data['videos']:
            identifier = (video['anime'], video['title'], video['url'])
            if identifier not in seen:
                seen.add(identifier)
                unique_videos.append(video)
        self.data['videos'] = unique_videos

    def view_unique_anime_names(self):
        """Returns a sorted list of all unique anime names."""
        return sorted(set(video['anime'] for video in self.data['videos']))

    def delete_by_anime_name(self, anime_name):
        """Deletes all records with the given anime name."""
        self.data['videos'] = [
            video for video in self.data['videos'] if video['anime'] != anime_name
        ]

    def get_data(self):
        """Returns the current state of the data."""
        return self.data

    def save(self, output_path=None):
        """Saves current data back to file. If output_path is given, saves to that file."""
        path = output_path if output_path else self.file_path
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
FILEPATH = "progress.json"
def read_progress(FILEPATH=FILEPATH):
    try:
        with open(FILEPATH, "r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def display_progress(FILEPATH=FILEPATH):
    last_mtime = None
    last_change_time = time()
    spinner = Spinner("dots")
    last_panel = None

    with Live(refresh_per_second=6, transient=True) as live:
        while True:
            if os.path.exists(FILEPATH):
                mtime = os.path.getmtime(FILEPATH)
                if mtime != last_mtime:
                    last_mtime = mtime
                    last_change_time = time()

                    progress = read_progress()
                    status = progress.get("status", "Waiting...")
                    song = progress.get("song_name", "")
                    link = progress.get("song_link", "")

                    spinner.text = ""

                    content = f"[bold]{status}[/bold]\n"
                    if song:
                        content += f"🎵 [cyan]{song}[/cyan]\n[blue underline]{link}[/blue underline]"

                    group = Group(spinner, content)
                    last_panel = Panel(group, title="Fetching Playlist")
                    live.update(last_panel)

                    if progress.get("done"):
                        break

            # If no update in 10s, show the last update once and break
            if time() - last_change_time > 10:
                if last_panel:
                    live.update(last_panel)  # re-show last known panel
                break

            #sleep(0.25)

def write_progress(info,FILEPATH=FILEPATH):
    dirpath = os.path.dirname(FILEPATH) or "."
    with tempfile.NamedTemporaryFile("w", dir=dirpath, delete=False) as tf:
        json.dump(info, tf)
        tempname = tf.name
    os.replace(tempname, FILEPATH)

def get_main_title(title):
    # Remove trailing parts like '2', '2nd Season', 'Final Season', 'II', 'III', 'Movie'
    pattern = r"(.*?)(\s\d+(st|nd|rd|th)?\s*Season|\sFinal Season|\sMovie.*|\sII+|\sIII+|\sIV+)?$"
    match = re.match(pattern, title, re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(":")
    return title

def multi_prompt(options,msg,current=-1):
    custom_style = {
        "question": "fg:#00fff7 bold",       # bright cyan (electric blue)
        "answer": "fg:#39ff14 bold",         # neon green
        "pointer": "fg:#ff0080 bold",        # hot pink / magenta
        "highlighted": "fg:#ff0080 bold",    # same as pointer (selected choice)
    }
    current_highlight = options[current]
    for idx, opt in enumerate(options):
        if idx == current and current != -1:
            options.insert(current,"🔥 " + current_highlight)
    prompt_option = prompt({"message": f"{msg}: ",
        "type": "fuzzy",
        "choices": options,
        "pointer": "▸"},style=custom_style)
    return prompt_option[0]

def load_all_unique_titles():
    data_manager = ConfigManager('saved_yt_links.json')
    data = data_manager.load()
    anime_titles = set()
    for video in data['videos']:
        raw_title = video['anime']
        clean_title = get_main_title(raw_title)
        anime_titles.add(clean_title)
    unique_anime_list = sorted(list(anime_titles))
    return unique_anime_list