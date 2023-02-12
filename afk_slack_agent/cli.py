"""Console script for afk_slack_agent."""
import sys
import click

from . import config


@click.command()
@click.option(
    "-v",
    "verbose",
    is_flag=False,
    default=False,
    help="More verbose logging.",
)
@click.option(
    "-a",
    "--agent",
    "as_agent",
    is_flag=True,
    default=False,
    help="Start as the agent server.",
)
@click.argument("action", required=False)
def main(verbose: bool = False, as_agent: bool = False, action: str = None):
    """AFK agent integration with Slack™.

    This command can be run as an agent or as a client.

    \b
    As an agent (-a), it will:
    - Capture your lock screen activation/deactivation and communicate them to Slack
    - Listen for messages from the client

    Using the client is optional. Agent can be used to send messages to the agent, to perform
    actions and run commands on your computer.

    Configuring action is done by editing the .afk.json file in your home directory.
    The file will be created the first time you run the agent.
    """
    if as_agent:
        click.echo("Starting as agent")
        config.check_or_create_config()
        from . import agent

        agent.main(verbose)
    else:
        click.echo("Starting as client")
        from . import client

        client.validate_action(action)
        client.main(verbose, action)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
