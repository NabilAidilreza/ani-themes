import threading
import time as ts
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.console import Group
from rich.table import Table
from rich.panel import Panel
from contextlib import contextmanager

TEXT_STYLES = {
    "success":     ("green1",        "[+]"),
    "failure":     ("red1",          "[-]"),
    "question":    ("deep_sky_blue1","[?]"),
    "warning":     ("gold1",         "[!]"),
    "processing":  ("medium_purple", "[*]"),
    "approx":      ("light_slate_grey", "[~]"),
    "user":        ("medium_purple", ""),     # No symbol
    "progress":    ("chartreuse1",   "[%]"),
    "comment":     ("grey54",        "[#]"),
    "dataout":     ("cyan1",         "[>]"),
    "datain":      ("dodger_blue1",  "[<]"),
    "fatal":       ("red3",          "[X]"),
    "finalok":     ("spring_green1", "(OK)"),
    "finalstop":   ("bright_red",    "(FAIL)"),
    "music":       ("hot_pink3",     "[♪]"),
}

def print(object, console=Console()):
    console.print(object)

def success(text, console=Console()):
    console.print("[green1][+] " + text + "[/green1]")

def failure(text, console=Console()):
    console.print("[red1][-] " + text + "[/red1]")

def question(text, console=Console()):
    console.print("[deep_sky_blue1][?] " + text + "[/deep_sky_blue1]", end="")
    return input("")

def warning(text, console=Console()):
    console.print("[gold1][!] " + text + "[/gold1]")

def processing(text, console=Console()):
    console.print("[medium_purple][*] " + text + "[/medium_purple]")

def approx(text, console=Console()):
    console.print("[light_slate_grey][~] " + text + "[/light_slate_grey]")

def user(text, console=Console()):
    console.print("[medium_purple]" + text + "[/medium_purple]")

def progress(text, console=Console()):
    console.print("[chartreuse1][%] " + text + "[/chartreuse1]")

def comment(text, console=Console()):
    console.print("[grey54]\[#] " + text + "[/grey54]")

def dataout(text, console=Console()):
    console.print("[cyan1][>] " + text + "[/cyan1]")

def datain(text, console=Console()):
    console.print("[dodger_blue1][<] " + text + "[/dodger_blue1]", end="")

def fatal(text, console=Console()):
    console.print("[red3][X] " + text + "[/red3]")

def finalok(text, console=Console()):
    console.print("[spring_green1](OK) " + text + "[/spring_green1]")

def finalstop(text, console=Console()):
    console.print("[bright_red](FAIL) " + text + "[/bright_red]")

def shutdown_countdown(seconds: int, console=Console()):
    for i in range(seconds, 0, -1):
        console.print(f"[bright_blue][^] Closing program in {i}s... [/bright_blue]", end="\r", highlight=False)
        ts.sleep(1)
    console.print(f"[bright_blue][^] Closing program now...   [/bright_blue]")

def music(title,status = "",context="", console=Console()):
    console.print(
        f"[hot_pink3][♪] {status}:[/hot_pink3] [bold white]{title}[/bold white] [grey53][/grey53] [bold cyan]{context}[/bold cyan]"
    )

def rich_text_anim(text,text_type,anim_seq=["", ".", "..", "..."], console=Console()):
    if text_type not in TEXT_STYLES:
        console.print(f"[red1][!] Unknown text type: '{text_type}'[/red1]")
        return
    
    color, symbol = TEXT_STYLES[text_type]
    stop_event = threading.Event()
    dots = anim_seq

    def run(live):
        i = 0
        while not stop_event.is_set():
            frame = f"[{color}]{symbol} {text}{dots[i % len(dots)]}[/{color}]"
            live.update(Text.from_markup(frame))
            i += 1
            ts.sleep(0.3)
        # On stop, update one last time with clean text (no dots)
        final_frame = f"[{color}]{symbol} {text}[/{color}]"
        live.update(Text.from_markup(final_frame))

    def target():
        with Live("", console=console, refresh_per_second=10, transient=True) as live:
            run(live)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return stop_event, thread

@contextmanager
def time_check():
    from time import time
    start = time()
    elapsed = {}
    yield elapsed   # yield a mutable container
    end = time()
    elapsed['elapsed'] = end - start

def run_with_animation(func, *args, text,text_type, show_time=True, **kwargs):
    console=Console()
    stop_event, thread = rich_text_anim(text,text_type)

    result = None
    with time_check() as tc:
        result = func(*args, **kwargs)
        stop_event.set()
        thread.join() # Prevent warning if already done
    if show_time:
        color, symbol = TEXT_STYLES.get(text_type, ("white", "[*]"))
        console.print(
            f"[{color}]{symbol} {text}[/{color}] [grey53](took {tc['elapsed']:.2f}s)[/grey53]"
        )
    return result


def run_with_animation_sync(func, *args, text, text_type, show_time=True, **kwargs):
    console = Console()
    
    start_time = ts.perf_counter()  # Start timer

    # You can keep your rich spinner/animation here if you want
    stop_event, thread = rich_text_anim(text, text_type)

    # Run the synchronous function
    result = func(*args, **kwargs)

    # Stop animation
    stop_event.set()
    thread.join()  # Ensure thread finishes

    elapsed = ts.perf_counter() - start_time

    # Print timing info
    if show_time:
        color, symbol = TEXT_STYLES.get(text_type, ("white", "[*]"))
        console.print(
            f"[{color}]{symbol} {text}[/{color}] [grey53](took {elapsed:.2f}s)[/grey53]"
        )

    return result