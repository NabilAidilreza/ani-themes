import json
import time
import logging
import subprocess
import pywintypes
import win32file
import win32pipe
import threading
from screeninfo import get_monitors
from playlist_generator import create_playlist_from_json,create_playlist_from_api
from utils import ConfigManager

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

config_manager = ConfigManager()
config = config_manager.load()
WINDOW_PRESET = config.get('ANI-THEMES-WINDOW-PLACEMENT','center')
HASJSON = config['ANI-THEMES-HASJSON']
YOUTUBE_API_KEY = config['YOUTUBE_API_KEY']
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
if config["YOUTUBE_API_CALL_COUNTER"] > 100:
    HASJSON = "True" 
config["CURRENT_INDEX"] = 0
config_manager.save(config)

#! Window Configuration
monitor = get_monitors()[0]  # Primary monitor
sw, sh = monitor.width, monitor.height
ww, wh = sw // 2, sh // 2
positions = {
    "top_left": (0, 0),
    "top_right": (sw // 2, 0),
    "bottom_left": (0, sh // 2),
    "bottom_right": (sw // 2, sh // 2),
    "center": (sw // 4, sh // 4),
}

#! Window Preset
preset = WINDOW_PRESET
px, py = positions[preset]
geometry = f"{ww}x{wh}+{px}+{py}"

#! Pipe
IPC_PIPE = r'\\.\pipe\mpvsocket'

mpv_proc = subprocess.Popen([
    "mpv",
    f"--input-ipc-server={IPC_PIPE}",
    "--title=Anime Theme Player",
    f"--geometry={geometry}",
    "--idle=yes",
    "--border=no",
    "--no-osd-bar",
    "--osd-level=0"#,
    #"--ontop"
])

time.sleep(1)

#! Pipe Connection
handle_read = None
while handle_read is None:
    try:
        handle_read = win32file.CreateFile(
            IPC_PIPE,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None, win32file.OPEN_EXISTING, 0, None
        )
    except pywintypes.error as e:
        if e.winerror == 2:  # ERROR_FILE_NOT_FOUND
            logging.info("Waiting for pipe...")
            time.sleep(0.5)
        else:
            raise

# timeout = 10
# start_time = time.time()
# handle_read = None
# while time.time() - start_time < timeout:
#     try:
#         handle_read = win32file.CreateFile(
#             IPC_PIPE,
#             win32file.GENERIC_READ | win32file.GENERIC_WRITE,
#             0, None, win32file.OPEN_EXISTING, 0, None
#         )
#         logging.info("[Controller] Connected to mpv IPC pipe.")
#         break
#     except pywintypes.error as e:
#         if e.winerror == 2:  # ERROR_FILE_NOT_FOUND
#             logging.info("Waiting for mpv IPC pipe...")
#             time.sleep(0.5)
#         else:
#             raise

# if handle_read is None:
#     logging.error("[Controller] Failed to connect to mpv IPC pipe after timeout.")
#     # Handle this error as needed (exit or retry)

def send_command(cmd):
    data = json.dumps(cmd) + "\n"
    win32file.WriteFile(handle_read, data.encode('utf-8'))

#! Variables for Logic Control
shutdown_event = threading.Event()
skip_next_endfile=False
single_mode = True
playlist_mode = False
playlist = []
titles = []
current_index = 0

#! Video Player Functions (Playlist)
def play_current():
    global current_index, skip_next_endfile
    url = playlist[current_index]
    skip_next_endfile = False
    send_command({"command": ["loadfile", url, "replace"]})

def next_video():
    global current_index, skip_next_endfile,config,config_manager
    if current_index >= len(playlist) - 1:
        logging.info("[Controller] Reached end of playlist on manual next. Reloading new playlist.")
        reload_new_playlist()
    current_index = (current_index + 1) % len(playlist)
    config['CURRENT_INDEX'] = current_index
    config_manager.save(config)
    skip_next_endfile = True
    send_command({"command": ["loadfile", playlist[current_index], "replace"]})
    
def previous_video():
    global current_index, skip_next_endfile,config,config_manager
    if current_index >= 0:
        current_index = (current_index - 1) % len(playlist)
        config['CURRENT_INDEX'] = current_index
        config_manager.save(config)
        skip_next_endfile = True
        send_command({"command": ["loadfile", playlist[current_index], "replace"]})

def replay_video():
    send_command({"command": ["seek", 0, "absolute"]})

def resume_video():
    send_command({"command": ["set_property", "pause", False]})

def pause_video():
    send_command({"command": ["set_property", "pause", True]})

def loop_video():
    send_command({"command": ["set_property", "loop", "inf"]})

def stoploop_video():
    send_command({"command": ["set_property", "loop", "no"]})

def reload_new_playlist():
    global playlist,titles, current_index,skip_next_endfile
    logging.info("[Controller] Reloading new playlist.")
    if HASJSON == "True":
        playlist, titles = create_playlist_from_json() 
    else:
        playlist = create_playlist_from_api(YOUTUBE_API_KEY,YOUTUBE_SEARCH_URL)
    current_index = 0 
    skip_next_endfile = True
    play_current()

def drain_pipe():
    while True:
        peek_result = win32pipe.PeekNamedPipe(handle_read, 0)
        avail_bytes = peek_result[1]
        if avail_bytes > 0:
            win32file.ReadFile(handle_read, 4096)
        else:
            break

def cleanup():
    shutdown_event.set()
    try:
        logging.info("[Controller] Sending quit command to mpv...")
        send_command({"command": ["quit"]})
        mpv_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logging.warning("[Controller] mpv did not exit in time, terminating...")
        mpv_proc.terminate()
        mpv_proc.wait()
    except pywintypes.error as e:
        # Handle invalid handle error gracefully during send_command
        if e.winerror == 6:  # ERROR_INVALID_HANDLE
            logging.warning("[Controller] Tried to send quit command on closed handle, ignoring.")
        else:
            logging.exception(f"[Controller] Unexpected error sending quit command: {e}")
    except Exception as e:
        logging.exception(f"[Controller] Error while shutting down mpv: {e}")
    try:
        if handle_read:
            win32file.CloseHandle(handle_read)
            logging.info("[Controller] Closed handle_read.")
    except Exception as e:
        logging.exception(f"[Controller] Error closing handle_read: {e}")
    try:
        if handle_controller:
            win32file.CloseHandle(handle_controller)
            logging.info("[Controller] Closed handle_controller.")
    except Exception as e:
        logging.exception(f"[Controller] Error closing handle_controller: {e}")
    # Join event_thread if it's not the current thread
    if threading.current_thread() != event_thread:
        event_thread.join(timeout=5)
    else:
        logging.warning("[Controller] Skipping join on event_thread (current thread).")
    # Join controller_thread if it's not the current thread
    if threading.current_thread() != controller_thread:
        controller_thread.join(timeout=5)
    else:
        logging.warning("[Controller] Skipping join on controller_thread (current thread).")
    logging.info("[Controller] All threads joined. Cleanup complete.")

#! Event listener thread
def listen_events():
    # Directly listens to mpv player events
    global current_index, skip_next_endfile, playlist_mode, single_mode, shutdown_event,config,config_manager
    while not shutdown_event.is_set():
        try:
            peek_result = win32pipe.PeekNamedPipe(handle_read, 0)
            avail_bytes = peek_result[1]
            if avail_bytes > 0:
                hr, raw = win32file.ReadFile(handle_read, 4096)
                if hr == 0:
                    messages = raw.decode("utf-8").strip().split("\n")
                    for msg in messages:
                        if msg:
                            obj = json.loads(msg)
                            if obj.get("event") == "end-file":
                                logging.info("[MPV] Video ended")
                                if skip_next_endfile:
                                    logging.info("[MPV] Skipping end-file (manual trigger)")
                                    skip_next_endfile = False
                                    continue  # skip the rest

                                if playlist_mode:
                                    if current_index == len(playlist) - 1:
                                        reload_new_playlist()
                                        config['CURRENT_INDEX'] = 0
                                        config_manager.save(config)
                                    else:
                                        skip_next_endfile = False
                                        current_index = (current_index + 1) % len(playlist)
                                        config['CURRENT_INDEX'] = current_index
                                        config_manager.save(config)
                                        next_url = playlist[current_index]
                                        send_command({"command": ["loadfile", next_url, "replace"]})
                                elif single_mode:
                                    replay_video()
            else:
                time.sleep(0.1)
        except Exception as e:
            break

#! Pipe
controller_pipe = win32pipe.CreateNamedPipe(
    r'\\.\pipe\controllerpipe',
    win32pipe.PIPE_ACCESS_DUPLEX,
    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
    1, 65536, 65536,
    0,
    None
)
logging.info("[Controller] Waiting for external connection on controllerpipe...")
win32pipe.ConnectNamedPipe(controller_pipe, None)
logging.info("[Controller] External controller connected!")
handle_controller = controller_pipe

# Start the named pipe server in a thread
# def start_controller_pipe():
#     global controller_pipe, handle_controller
#     controller_pipe = win32pipe.CreateNamedPipe(
#         r'\\.\pipe\controllerpipe',
#         win32pipe.PIPE_ACCESS_DUPLEX,
#         win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
#         1, 65536, 65536,
#         0,
#         None
#     )
#     logging.info("[Controller] Waiting for external connection on controllerpipe...")
#     win32pipe.ConnectNamedPipe(controller_pipe, None)
#     logging.info("[Controller] External controller connected!")
#     handle_controller = controller_pipe

# pipe_thread = threading.Thread(target=start_controller_pipe, daemon=True)
# pipe_thread.start()


#! Controller listening thread
def listen_controller():
    # Logic control for user to mpv player
    global playlist, titles, single_mode, playlist_mode, current_index, shutdown_event,config,config_manager
    while not shutdown_event.is_set():
        try:
            hr, raw = win32file.ReadFile(handle_controller, 4096)
            if hr == 0:
                msg = raw.decode("utf-8").strip()
                logging.info(f"[Controller Pipe] Raw received: {msg}")  # log raw incoming
                
                try:
                    obj = json.loads(msg)
                except json.JSONDecodeError:
                    logging.warning("[Controller] ⚠ Invalid JSON received, skipping.")
                    continue

                command = obj.get("command")
                data = obj.get("data")

                if command:
                    logging.info(f"[Controller] Parsed command: {command}")
                    if command == "ping":
                        logging.info("[Controller] Received ping command, responding...")
                        win32file.WriteFile(handle_controller, b'{"response": "pong"}\n')
                    if command == "loadplaylist":
                        single_mode = False
                        playlist_mode = True
                        if HASJSON == "True":
                            playlist, titles = create_playlist_from_json()
                        else:
                            playlist, titles = create_playlist_from_api(YOUTUBE_API_KEY,YOUTUBE_SEARCH_URL)
                        config['CURRENT-PLAYLIST'] = titles
                        config_manager.save(config)
                        current_index = 0
                        play_current()
                    elif command == "loadsingle":
                        single_mode = True
                        playlist_mode = False
                        url = data.get('url') if data else None
                        if not url:
                            logging.warning("[Controller] No URL provided for loadsingle command.")
                            continue
                        playlist = [url]
                        current_index = 0
                        play_current()
                    elif command == "loadsingle_queue":
                        single_mode = False
                        playlist_mode = True
                        playlist.append(data['url'])
                    elif command == "next":
                        next_video()
                    elif command == "prev":
                        previous_video()
                    elif command == "replay":
                        replay_video()
                    elif command == "resume":
                        resume_video()
                    elif command == "pause":
                        pause_video()
                    elif command == "loop":
                        loop_video()
                    elif command == "stoploop":
                        stoploop_video()
                    elif command == "quit":
                        cleanup()
                    else:
                        logging.warning(f"[Controller] ⚠ Unknown command received: {command}")
                else:
                    logging.warning("[Controller] ⚠ No 'command' or 'custom_command' field found.")
        except pywintypes.error as e:
            if e.winerror == 109:  # pipe has been ended
                logging.info("[Controller] Pipe closed, exiting thread.")
                break
            else:
                raise

#! Initialize Threads
event_thread = threading.Thread(target=listen_events, daemon=True)
controller_thread = threading.Thread(target=listen_controller, daemon=True)
event_thread.start()
controller_thread.start()

#! Keep script alive
try:
    mpv_proc.wait()
except KeyboardInterrupt:
    logging.info("Keyboard interrupt, shutting down...")
finally:
    cleanup()