"""AFK Client for agent."""

import sys
from multiprocessing.connection import Client

import click

from . import config


def validate_action(action: str):
    if not action:
        click.echo("No action provided. Action is required when running the client.")
        sys.exit(1)
    actions = [a.get("action") for a in config.get_config("actions") if a.get("action")] + [
        "terminate"
    ]
    if action not in actions:
        click.echo(f"Action \"{action}\" is not valid. Valid actions are {', '.join(actions)}")
        sys.exit(1)


def main(verbose: bool = False, action: str = None):
    try:
        conn = Client("/tmp/slack_afk_agent", "AF_UNIX")
        click.echo(f"Sending {action}")
        conn.send(action)
        conn.close()
    except FileNotFoundError:
        click.echo("Error: is agent running?")
