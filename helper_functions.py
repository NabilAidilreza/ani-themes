import re
import json
# import importlib.resources
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
    data_manager = ConfigManager('yt_anithemes_links.json')
    data = data_manager.load()
    anime_titles = set()
    for video in data['videos']:
        raw_title = video['anime']
        clean_title = get_main_title(raw_title)
        anime_titles.add(clean_title)
    unique_anime_list = sorted(list(anime_titles))
    return unique_anime_list