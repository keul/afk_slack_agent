===============
AFK Slack Agent
===============


.. image:: https://img.shields.io/pypi/v/afk_slack_agent.svg
        :target: https://pypi.python.org/pypi/afk_slack_agent

Signal you A.F.K. (Away From Keyboard) status on Slack, automatically.

.. contents:: Table of Contents

.. warning::
    This software is for MacOS only!

Installation
============

.. code-block:: bash
   
   pip install afk_slack_agent

What it does?
=============

This software is distributed with an agent (``afk_agent``) and a client (``afk``, optional).

The agent is designed to be run in the background and stay active until you terminate it.

Features implemented by the agent

- waits for lock screen and unlock screen events (*very buggy* feature, due to changes in behavior in *every* MacOS release 😮‍💨)
- connects to a Slack workspace, and change user status on lock (clean it on unlock)
- optionally: write a message on a channel on lock/unlock

Prerequisites
=============

- you have to `create a Slack application <https://api.slack.com/apps?new_app=1>`_, and install it into your workspace
  - the application should have at least the following `scope <https://api.slack.com/scopes>`_: ``users.profile:write``.
    
    optionally, you could also enable ``chat:write`` and ``reactions:write``
- to run custom AFK commands from the client, you'll need to enable the agent to control your Mac (from "Privacy and Security" system settings)

How to use
==========

Run ``afk --help`` for a list of all commands.

In brief: when the agent is running, you can run ``afk <action>`` to interact with slack.

Actions must be customized in you ``.afk`` file (see below), apart for:

- ``terminate`` - kill the agent
- ``back``- signal Slack you are BTK

Configuration
=============

The first time the agent is run, a ``~/.afk.json`` file is created.

This is the default file created:

.. code-block:: json
   
   {
     "version": 1,
     "token": "",
     "status_text": "I need a break",
     "status_emoji": ":coffee:",
     "channel": null,
     "away_message": "I'm going to take a coffee break",
     "back_message": "I'm back",
     "delay_for_reaction_emoji": 60,
     "back_emoji": "back",
     "agent_emoji": "robot_face",
     "agent_active_start_time": null,
     "agent_active_end_time": null,
     "actions": [
       {
         "action": "lunch",
         "status_text": "Lunch break",
         "status_emoji": ":spaghetti:",
         "away_message": "I'm going to take the lunch break",
         "back_message": "I'm back and stuffed!",
         "command": "lock"
       }
     ]
   }

The most important key is ``token``, which must contain the Slack User OAuth Token.

.. image:: https://raw.githubusercontent.com/keul/afk_slack_agent/main/docs/slack-key.png
        :alt: Slack configuration, where to grab your token

Other settings
--------------

``status_text``
  Status to be set when locking the screen

``status_emoji``
  emoji to be set when locking the screen

``channel``
  use this only if you want to write messages on a channel when going AFK and be back.
  
  Put the channel id there. You can find it by right-clicking on the channel and clicking "View channel details".
  It will be at the very bottom of the popup.

``away_message``
  message to send when going  AFK

``back_message``
  message to send when back to keyboard

``delay_for_reaction_emoji``
  in case you will be back before this amount of seconds, do not send a back message, but just react to your away message using a reaction emoji.
  This will reduce noise in case of quick lock/unlock screen

``back_emoji``
  emoji to be used for quick back reaction

``agent_emoji``
  automatically adds this emoji at the end of every message sent or slack status set.
  This helps others to know there's a bot that is acting for you.

``delay_after_screen_lock``
  before starting interacting with Slack, wait this amount of seconds.

  This will delay reactions to your lock screen status a while, so no Slack commands will be run if you unlock the screen before this time.
  As example: you are reading a document and the screen locks for inactivity, but you are not AFK.

``agent_active_start_time`` and ``agent_active_end_time``
  time range inside which agent is effectively working.

  When provided (in the format as ``HH:MM``), the agent will only effectively works when current time is inside this (potentially open) time range.
  This can be used to disable the agent when using your computer outside working hours.

  This is not applied to explicit actions (``afk <command>``).

Custom actions
~~~~~~~~~~~~~~

The JSON configuration can contain an ``actions`` key, with an array of *custom actions*.

Custom actions can be sent to the agent using the client component:

.. code-block:: bash
   
   afk lunch

A custom action is a way to perform something more than the standard lock/unlock monitor.

See the ``afk`` command line help for more.

An action interact with Slack in the same way the agent does, and inherit the same configuration, but it can override some of them like: ``status_text``, ``status_emoji``, ``away_message`` and ``back_message``.
Every of these settings can be ``null`` to explicitly inherit from the global settings.
``back_message`` can also be ``false``: this disables the back message for the action even if the global setting has a value.

Finally, a custom action can perform one of the following commands:

``lock``
  Lock the screen manually

``sleep``
  Put you computer to sleep

If no ``command`` is defined or it's ``null``, the interaction with Slack will be run immediately (same as providing the ``--no-command`` option at the command line).

Why?
====

To understand motivation about this tool, read `why I needed to join my lock screen activities with Slack <https://blog.keul.it/automate-slack-afk-status/>`_.
