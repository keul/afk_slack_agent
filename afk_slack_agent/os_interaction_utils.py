"""
See https://betterprogramming.pub/custom-system-notifications-from-python-mac-5ff42e71214
See also https://apple.stackexchange.com/questions/135728/using-applescript-to-lock-screen
"""

import subprocess


def sleep():
    subprocess.Popen("""osascript -e 'tell application "Finder" to sleep'""", shell=True)


def lock_screen():
    subprocess.Popen(
        (
            """osascript -e 'tell application "System Events" to keystroke"""
            """ "q" using {control down, command down}'"""
        ),
        shell=True,
    )
