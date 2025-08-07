from rich.table import Table
from rich.live import Live
from rich.console import Console
from time import sleep

from utils import ConfigManager

config_manager = ConfigManager()


def read_current_song():
    try:
        config = config_manager.load()
        return config.get("CURRENT_INDEX")
    except:
        return 0
    
def get_songs():
    try:
        config = config_manager.load()
        return config.get("CURRENT-PLAYLIST")
    except:
        return 0

def create_playlist_table(songs,current_song_idx):
    table = Table(title=f"Now Playing: {songs[current_song_idx][0]} by {songs[current_song_idx][1]}", show_header=True, header_style="bold magenta")
    table.add_column("Track", style="cyan", width=5)
    table.add_column("Song Title", style="green")
    table.add_column("Anime", style="blue")
    table.add_column("Status", justify="center", style="yellow")

    for idx, (title, artist) in enumerate(songs, 1):
        status = "▶ Playing" if idx - 1 == current_song_idx else ""
        row_style = "bold on #1e1e1e" if idx - 1 == current_song_idx else None
        table.add_row(str(idx), title, artist, status, style=row_style)

    return table

console = Console()
songs = get_songs()
with Live(create_playlist_table(songs,read_current_song()), refresh_per_second=10, console=console) as live:
    while True:
        idx = read_current_song()
        live.update(create_playlist_table(songs,idx))
        sleep(1)
