"""
See https://betterprogramming.pub/custom-system-notifications-from-python-mac-5ff42e71214
See also https://apple.stackexchange.com/questions/135728/using-applescript-to-lock-screen
"""

import os
import subprocess


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
