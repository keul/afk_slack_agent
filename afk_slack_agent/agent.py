"""Agent module."""

import os
import logging
import sys
import time
import atexit
from dataclasses import dataclass
from multiprocessing.connection import Listener
from threading import Thread
import datetime
import psutil

import click

import Foundation
from AppKit import NSObject
from PyObjCTools import AppHelper

from slack_sdk import WebClient

from .config import get_config, check_or_create_config, SOCKET_DESCRIPTOR
from . import os_interaction_utils

client = None
afk_thread = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def compute_message(message):
    if get_config("agent_emoji"):
        return f"{message} (:{get_config('agent_emoji')}:)"
    return message


def get_unix_time(plus_seconds=0):
    """Get the current unix time.

    Adds plus_seconds to the current time if seconds is not None.
    """
    return int(time.time()) + plus_seconds


@dataclass
class Status:
    im_afk: bool = False
    going_afk: bool = False
    last_message_ts: str = None
    last_activity_ts: int = get_unix_time()

    def __str__(self) -> str:
        return (
            f"Status(im_afk={self.im_afk}, going_afk={self.going_afk} "
            f"last_message_ts={self.last_message_ts}, "
            f"last_activity_ts={self.last_activity_ts})"
        )


class NextSlackStatus:
    def __init__(self):
        self.status_text: str = get_config("status_text")
        self.status_emoji: str = get_config("status_emoji")
        self.away_message: str = get_config("away_message")
        self.back_message: str = get_config("back_message")

    def __str__(self) -> str:
        return (
            f"NextSlackStatus(status_text={self.status_text}, status_emoji={self.status_emoji}, "
            f"away_message={self.away_message}, back_message={self.back_message})"
        )


status = None
slack_status = None


def check_slack_is_active():
    ls = []
    for p in psutil.process_iter(["name"]):
        if p.info["name"] == "Slack":
            ls.append(p)
    return len(ls) > 0


def handleBack(afk_delay=None):
    global slack_status
    logger.debug("status: %s", slack_status)

    if not agent_is_active():
        os_interaction_utils.system_message("We are is oustide active time range. Doing nothing")
        return

    if status.going_afk and not status.im_afk:
        # Come back before fully going AFK. Do nothing
        click.echo("Back before fully going AFK. Abort")
        status.going_afk = False
        return
    status.im_afk = False
    status.going_afk = False
    try:
        click.echo("Setting back status")
        client.api_call(
            api_method="users.profile.set",
            params={
                "profile": {
                    "status_text": "",
                    "status_emoji": "",
                    "status_expiration": "",
                }
            },
        )
        if get_config("channel") and slack_status.back_message:
            # 1. if you are back in less than "delay_for_reaction_emoji" seconds, use an emoji
            if (
                status.last_message_ts
                and status.last_activity_ts + get_config("delay_for_reaction_emoji")
                > get_unix_time()
            ):
                click.echo("Reacting to last message")
                client.reactions_add(
                    channel=get_config("channel"),
                    name=get_config("back_emoji"),
                    timestamp=status.last_message_ts,
                )
                return
            # 2. reply with an explicit message
            click.echo("Sending back message")
            client.chat_postMessage(
                channel=get_config("channel"),
                text=compute_message(slack_status.back_message),
            )
    except Exception as e:
        click.echo(f"Error: {e}")
    finally:
        # Reset next slack status
        slack_status = NextSlackStatus()


def handleAFK(afk_delay=None):
    status.going_afk = True

    def _perform_afk():

        if not agent_is_active():
            os_interaction_utils.system_message(
                "We are is oustide active time range. Doing nothing"
            )
            return

        # Delay the AFK handling
        delay = get_config("delay_after_screen_lock", 0) if afk_delay is None else afk_delay
        click.echo(f"sleeping for {delay}")
        time.sleep(delay)
        if not status.going_afk:
            # user probably went back before the delay
            click.echo("Not going AFK anymore. Doing nothing")
            return
        status.im_afk = True
        try:
            click.echo("Setting away status")
            client.api_call(
                api_method="users.profile.set",
                params={
                    "profile": {
                        "status_text": compute_message(slack_status.status_text),
                        "status_emoji": slack_status.status_emoji,
                        "status_expiration": 0,
                    }
                },
            )
            logger.debug("slack status: %s", slack_status)
            if get_config("channel") and slack_status.away_message:
                click.echo("Sending away message")
                data = client.chat_postMessage(
                    channel=get_config("channel"),
                    text=compute_message(slack_status.away_message),
                )
                status.last_message_ts = data["ts"]
                status.last_activity_ts = get_unix_time()
        except Exception as e:
            click.echo(f"Error: {e}")

    global afk_thread
    afk_thread = Thread(target=_perform_afk, daemon=True)
    afk_thread.start()


def agent_is_active():
    """Check if the agent is active based on the time range configuration."""
    start_time = get_config("agent_active_start_time")
    end_time = get_config("agent_active_end_time")
    now = datetime.datetime.now().time().strftime("%H:%M")
    if (
        (start_time and end_time and now < start_time or now > end_time)
        or (start_time and now < start_time)
        or (end_time and now > end_time)
    ):
        click.echo("We are is oustide active time range. Doing nothing")
        return False
    return True


class HandleScreenLock(NSObject):
    def getScreenIsLocked_(self, notification):
        click.echo("Screen has been locked")
        if not check_slack_is_active():
            click.echo("Slack client is not active. Doing nothing")
            return
        if status.im_afk:
            click.echo("Already away. Doing nothing")
            return
        handleAFK()

    def getScreenIsUnlocked_(self, notification):
        click.echo("Screen has been unlocked")
        if not check_slack_is_active():
            click.echo("Slack client is not active. Doing nothing")
            return
        handleBack()


screenLockHandler = HandleScreenLock.new()


def exit_handler():
    click.echo("Exiting")
    nc.removeObserver_(screenLockHandler)


nc = Foundation.NSDistributedNotificationCenter.defaultCenter()
nc.addObserver_selector_name_object_(
    screenLockHandler, "getScreenIsLocked:", "com.apple.screenIsLocked", None
)

nc.addObserver_selector_name_object_(
    screenLockHandler, "getScreenIsUnlocked:", "com.apple.screenIsUnlocked", None
)


def find_action(msg):
    actions = get_config("actions")
    action_conf = None
    for action in actions:
        if action.get("action") == msg:
            action_conf = action
            break
    return action_conf


def _property_getter(prop, custom, action):
    """Get a property from a set of sources.

    Try from the client execution custom options.
    Fallback to the action configuration.
    Fallback again to the global configuration.
    """
    return custom.get(prop) or action.get(prop, "") or get_config(prop)


def fill_slack_status(custom_message: dict, action_conf: dict):
    logger.debug(f"filling slack status with {custom_message}, {action_conf}")
    silent = custom_message.get("silent", False)
    slack_status.status_text = _property_getter("status_text", custom_message, action_conf)
    slack_status.status_emoji = _property_getter("status_emoji", custom_message, action_conf)
    if not silent:
        slack_status.away_message = _property_getter("away_message", custom_message, action_conf)
    else:
        slack_status.away_message = None
    if action_conf.get("back_message", "") is not False and not silent:
        slack_status.back_message = action_conf.get("back_message", "") or get_config(
            "back_message"
        )
    else:
        slack_status.back_message = None
    logger.debug(f"new slack status: {slack_status}")


def execute_command(command):
    if not command:
        return
    click.echo(f'Executing command "{command}"')
    match command:
        case "sleep":
            os_interaction_utils.sleep()
        case "lock":
            os_interaction_utils.lock_screen()
        case _:
            click.echo(f"Unknown command {command}")


def listen_for_messages():
    try:
        os.unlink(SOCKET_DESCRIPTOR)
    except FileNotFoundError:
        pass
    listener = Listener(SOCKET_DESCRIPTOR, "AF_UNIX")
    conn = listener.accept()
    while True:
        msg = None
        try:
            msg = conn.recv()
        except EOFError:
            conn = listener.accept()
            continue
        click.echo(f"Message: {msg}")
        # check is Slack is running
        if not check_slack_is_active():
            click.echo("Slack client is not active. Doing nothing")
            continue
        # do something with msg
        if msg["action"] == "terminate":
            click.echo("Received termination request. Exiting")
            conn.close()
            AppHelper.stopEventLoop()
            break
        # Now looks for user defined actions
        action = find_action(msg["action"])
        if not action:
            click.echo(f"Action {msg['action']} not found")
            continue
        # Execute the action
        click.echo(f"Executing user defined action: {action}")
        fill_slack_status(msg, action)
        if not msg.get("no_command"):
            execute_command(action.get("command"))
        else:
            logger.debug("Manually triggering the configuration for this action")
            handleAFK(0)
    listener.close()
    sys.exit(0)


@click.command()
@click.option(
    "-v",
    "verbose",
    is_flag=True,
    default=False,
    help="More verbose logging.",
)
def main(verbose: bool = False):
    """AFK agent integration with Slack™.

    This command runs a Slack integration agent on the system.

    \b
    As an agent (-a), it will:
    - Capture your lock screen activation/deactivation and communicate them to Slack
    - Listen for messages from the client

    Configuring actions is done by editing the .afk.json file in your home directory.
    The file will be created the first time you run the agent.
    """
    global client
    global slack_status
    global status
    click.echo("AFK agent: starting…")
    check_or_create_config()
    slack_status = NextSlackStatus()
    status = Status()
    atexit.register(exit_handler)
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    token = get_config("token")
    if not token:
        click.echo("Please, fill the token setting in the config file")
        sys.exit(1)
    # 1. start a thread to listen for incoming messages
    messages_thread = Thread(target=listen_for_messages, daemon=True)
    messages_thread.start()
    # 2. wait for system messages
    client = WebClient(token=token)
    AppHelper.runConsoleEventLoop()


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
