from rich.console import Console

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
    console.print("[dodger_blue1][<] " + text + "[/dodger_blue1]")

def fatal(text, console=Console()):
    console.print("[red3][X] " + text + "[/red3]")

def finalok(text, console=Console()):
    console.print("[spring_green1](OK) " + text + "[/spring_green1]")

def finalstop(text, console=Console()):
    console.print("[bright_red](FAIL) " + text + "[/bright_red]")
