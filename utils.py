import os
import re
import json
from contextlib import contextmanager
# import importlib.resources
import tempfile
from time import sleep,time
from rich.live import Live
from rich.console import Group
from rich.spinner import Spinner
from rich.panel import Panel
from rich.align import Align
from InquirerPy import prompt

class ConfigManager:
    def __init__(self,path = "config.json"):
        # self.path = importlib.resources.files("ani_themes") / "config.json"
        self.path = path
        self.load()
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

@contextmanager
def time_check():
    from time import time
    start = time()
    elapsed = {}
    yield elapsed   # yield a mutable container
    end = time()
    elapsed['elapsed'] = end - start

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
            # Add an emoji or marker to highlight
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


PROGRESS_FILE = "progress.json"

def read_progress(filepath=PROGRESS_FILE):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception:
        return None

def display_progress():
    last_mtime = None
    last_change_time = time()
    spinner = Spinner("dots")
    last_panel = None

    with Live(refresh_per_second=10, transient=True) as live:
        while True:
            if os.path.exists(PROGRESS_FILE):
                mtime = os.path.getmtime(PROGRESS_FILE)
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

            sleep(0.25)

def write_progress(info, filepath=PROGRESS_FILE):
    dirpath = os.path.dirname(filepath) or "."
    with tempfile.NamedTemporaryFile("w", dir=dirpath, delete=False) as tf:
        json.dump(info, tf)
        tempname = tf.name
    os.replace(tempname, filepath)


def remove_duplicates(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    seen = set()
    unique = []

    for entry in data["videos"]:
        key = (entry["title"].strip().lower(), entry["url"].strip())
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"videos": unique}, f, indent=4, ensure_ascii=False)

    print(f"✅ Removed duplicates. {len(data['videos']) - len(unique)} duplicates found.")
    print(f"📁 Output saved to: {output_file}")

# # Example usage
# remove_duplicates("saved_yt_links.json", "saved_yt_links_c.json")