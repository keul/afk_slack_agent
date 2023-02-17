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
        "terminate"
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
@click.argument("action", required=False)
def main(verbose: bool = False, action: str = None):
    """Client for AFK agent integration with Slack™.

    This command connects to the afk_agent process, to runs actions on the system.

    Configuring actions is done by editing the .afk.json file in your home directory.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    click.echo("AFK client: starting…")
    validate_action(action)
    try:
        conn = Client(config.SOCKET_DESCRIPTOR, "AF_UNIX")
        click.echo(f"Sending {action}")
        conn.send(action)
        conn.close()
    except FileNotFoundError:
        click.echo("Error: is agent running?")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
