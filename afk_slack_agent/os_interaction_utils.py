"""
See https://betterprogramming.pub/custom-system-notifications-from-python-mac-5ff42e71214
See also https://apple.stackexchange.com/questions/135728/using-applescript-to-lock-screen
"""

import os
import subprocess
import psutil


def sleep():
    # On some MacOS version the system geos to sleep very quickly, and the program is halted too quickly
    subprocess.Popen("""osascript -e 'tell application "Finder" to sleep'""", shell=True)


def lock_screen():
    subprocess.Popen(
        (
            """osascript -e 'tell application "System Events" to keystroke"""
            """ "q" using {control down, command down}'"""
        ),
        shell=True,
    )


def system_message(message):
    os.system(
        """osascript -e 'display notification "{}" with title "{}"'""".format(
            message,
            "AFK Agent",
        )
    )


def check_slack_is_active():
    ls = []
    for p in psutil.process_iter(["name"]):
        if p.info["name"] == "Slack":
            ls.append(p)
    return len(ls) > 0


def kill_agent():
    pid = os.getpid()
    system_message("Killing AFK agent…")
    psutil.Process(pid).kill()
