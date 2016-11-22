=======
DankBot
=======

A small slackbot to post EVE kills to Slack.

============
Installation
============

This project is not production ready, so these instructions are intentionally sparse.

1. Download the repository.
2. pip install -r requirements.txt
3. Make a copy of the two config files removing .example from the name, and input your own params.
4. Run ./dankbot_run.py

--------------------
Command line options
--------------------

--nodaemon / will run the bot in the terminal

--config PATH / lets you specify a path to the config files

====
Todo
====

1. Clean up prints into logging with levels.
2. Enable logging to file when in daemon mode.
3. Run config validation at startup
