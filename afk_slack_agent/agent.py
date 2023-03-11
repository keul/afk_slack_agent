"""Agent module."""

import os
import logging
import sys
import time
import atexit
from dataclasses import dataclass
import psutil
from multiprocessing.connection import Listener
from threading import Thread

import click

import Foundation
from AppKit import NSObject
from PyObjCTools import AppHelper

from slack_sdk import WebClient

from .config import get_config, check_or_create_config, SOCKET_DESCRIPTOR
from . import os_interaction_utils

client = None
check_or_create_config()


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
    last_message_ts: str = None
    last_activity_ts: int = get_unix_time()

    def __str__(self) -> str:
        return (
            f"Status(im_afk={self.im_afk}, last_message_ts={self.last_message_ts}, "
            f"last_activity_ts={self.last_activity_ts})"
        )


@dataclass
class NextSlackStatus:
    status_text: str = get_config("status_text")
    status_emoji: str = get_config("status_emoji")
    away_message: str = get_config("away_message")
    back_message: str = get_config("back_message")

    def __str__(self) -> str:
        return (
            f"NextSlackStatus(status_text={self.status_text}, status_emoji={self.status_emoji}, "
            f"away_message={self.away_message}, back_message={self.back_message})"
        )


status = Status()
slack_status = NextSlackStatus()


def check_slack_is_active():
    ls = []
    for p in psutil.process_iter(["name"]):
        if p.info["name"] == "Slack":
            ls.append(p)
    return len(ls) > 0


def handleBack():
    global slack_status
    status.im_afk = False
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
    return slack_status


def handleAFK():
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
        logging.debug("slack status: %s", slack_status)
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


class HandleScreenLock(NSObject):
    def getScreenIsLocked_(self, notification):
        click.echo("Screen has been locked")
        if not check_slack_is_active():
            click.echo("Slack client is not active. Doing nothing")
            return
        if status.im_afk:
            logging.debug("Already away. Doing nothing")
            return
        handleAFK()

    def getScreenIsUnlocked_(self, notification):
        click.echo("Screen has been unlocked")
        if not check_slack_is_active():
            click.echo("Slack client is not active. Doing nothing")
            return
        if not status.im_afk:
            logging.debug("Already back. Doing nothing")
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
    logging.debug(f"filling slack status with {custom_message}, {action_conf}")
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
    logging.debug(f"new slack status: {slack_status}")


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
        # do something with msg
        if msg["action"] == "terminate":
            click.echo(f"Received termination request. Exiting")
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
        execute_command(action.get("command"))
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
    click.echo("AFK agent: starting…")
    check_or_create_config()
    atexit.register(exit_handler)
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    token = get_config("token")
    if not token:
        click.echo("Please, fill the token setting in the config file")
        sys.exit(1)
    # 1. start a thread to listen for incoming messages
    messages_thread = Thread(target=listen_for_messages)
    messages_thread.daemon = True
    messages_thread.start()
    # 2. wait for system messages
    client = WebClient(token=token)
    AppHelper.runConsoleEventLoop()


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
