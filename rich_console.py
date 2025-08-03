import threading
import time as ts
from rich.console import Console
from rich.live import Live
from rich.text import Text

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

def datain_anim(text, console=Console()):
    stop_event = threading.Event()
    dots = ["", ".", "..", "...", " ..", " ."]

    def run(live):
        i = 0
        while not stop_event.is_set():
            frame = f"[dodger_blue1][<] {text}{dots[i % len(dots)]}[/dodger_blue1]"
            live.update(Text.from_markup(frame))
            i += 1
            ts.sleep(0.3)
        # On stop, update one last time with clean text (no dots)
        final_frame = f"[dodger_blue1][<] {text}[/dodger_blue1]"
        live.update(Text.from_markup(final_frame))

    def target():
        with Live("", console=console, refresh_per_second=10, transient=True) as live:
            run(live)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return stop_event, thread

def fatal(text, console=Console()):
    console.print("[red3][X] " + text + "[/red3]")

def finalok(text, console=Console()):
    console.print("[spring_green1](OK) " + text + "[/spring_green1]")

def finalstop(text, console=Console()):
    console.print("[bright_red](FAIL) " + text + "[/bright_red]")

def music(title,status = "",context="", console=Console()):
    console.print(
        f"[hot_pink3][♪] {status}:[/hot_pink3] [bold white]{title}[/bold white] [grey53][/grey53] [bold cyan]{context}[/bold cyan]"
    )
