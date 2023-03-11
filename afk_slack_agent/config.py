"""Configuration management."""

import os
import sys
import json

import click
from pathlib import Path

config = {}
home = str(Path.home())
config_file = os.path.join(home, ".afk.json")

SOCKET_DESCRIPTOR = "/tmp/slack_afk_agent"

CONFIG_VERSION = 1

DEFAULT_JSON = {
    "token": "",
    "status_text": "I need a break",
    "status_emoji": ":coffee:",
    # This for also writing a message to a channel (requires `chat:write` scope)
    "channel": None,
    "away_message": "I'm going to take a coffee break",
    "back_message": "I'm back",
    # emoji (without ":"s) to be used instead of the back_message (requires `reactions:write` scope)
    "back_emoji": "back",
    # adds this emoji as " (<emoji_here)"" to every message, to warn reader this is an automated message
    "agent_emoji": "robot_face",
    # delay in seconds to use the back_emoji instead of the back_message
    "delay_for_reaction_emoji": 60,
    "actions": [
        {
            "action": "lunch",
            # This for also writing a message to a channel (requires `chat:write` scope)
            "status_text": "Lunch break",
            "status_emoji": ":spaghetti:",
            "away_message": "I'm going to take the lunch break",
            # Use boolean false to not send back message or reaction, null to inherit from global
            "back_message": "I'm back and stuffed!",
            "command": "lock",
        },
    ],
}


def get_config(key):
    global config
    with open(config_file, "r") as f:
        config = json.load(f)
    return config.get(key)


def check_or_create_config():
    """Generate a ".afk.json" file in the home folder if it doesn't exist."""
    if not os.path.exists(config_file):
        click.echo(f"config file not found: creating {config_file}")
        with open(config_file, "w") as f:
            json.dump({"version": CONFIG_VERSION, **DEFAULT_JSON}, f, indent=4)
        click.echo('Please, fill the "token" setting and try again')
        click.echo(
            "Please note! You need at least `users.profile:write` scope "
            "(`chat:write` required to write on a channel too)"
        )
        sys.exit(1)
    # If there: evalute if we need to merge/update current JSON (in case it's not up to date)
    with open(config_file, "r") as f:
        config = json.load(f)
        if CONFIG_VERSION != config.get("version"):
            click.echo(f"Config file is not up to date: updating {config_file}")
            with open(config_file, "w") as f:
                json.dump({**DEFAULT_JSON, **config, "version": CONFIG_VERSION}, f, indent=4)
