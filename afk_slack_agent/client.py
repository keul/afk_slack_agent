"""AFK Client for agent."""

import sys
import logging
from multiprocessing.connection import Client

import click

from . import config


def validate_action(action: str):
    if not action:
        click.echo("No action provided. Action is required when running the client.")
        sys.exit(1)
    actions = [a.get("action") for a in config.get_config("actions") if a.get("action")] + [
        "terminate",
        "back",
    ]
    if action not in actions:
        click.echo(f"Action \"{action}\" is not valid. Valid actions are {', '.join(actions)}")
        sys.exit(1)


@click.command()
@click.option(
    "-v",
    "verbose",
    is_flag=True,
    default=False,
    help="More verbose logging.",
)
@click.option(
    "-s",
    "--status",
    default="",
    help="Custom status for the AFK action.",
)
@click.option(
    "-e",
    "--emoji",
    default="",
    help="Custom status emoji for the AFK action.",
)
@click.option(
    "-m",
    "--away-message",
    "away_message",
    default="",
    help="Custom away message for the AFK action.",
)
@click.option(
    "--silent",
    is_flag=True,
    default=False,
    help="Do not write messages for this action.",
)
@click.option(
    "--no-command",
    is_flag=True,
    default=False,
    help="Do not execute command configured for this action.",
)
@click.argument("action", required=False)
def main(
    verbose: bool = False,
    status: str = "",
    emoji: str = "",
    away_message: str = "",
    action: str = None,
    silent: bool = False,
    no_command: bool = False,
):
    """Client for AFK agent integration with Slack™.

    This command connects to the afk_agent process, to runs actions on the system.
    Configuring actions is done by editing the .afk.json file in your home directory.
    Action can be overridden by using options.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    click.echo("AFK client: starting…")
    validate_action(action)
    try:
        conn = Client(config.SOCKET_DESCRIPTOR, "AF_UNIX")
        click.echo(f"Sending {action}")
        conn.send(
            {
                "action": action,
                "status_text": status,
                "status_emoji": emoji,
                "away_message": away_message,
                "silent": silent,
                "no_command": no_command,
            }
        )
        conn.close()
    except (FileNotFoundError, ConnectionRefusedError):
        click.echo("Error: is agent running?")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
