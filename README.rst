=======
DankBot
=======

A small slackbot to post EVE kills to Slack.

============
Installation
============

This project is not production ready, so these instructions are intentionally sparse.

1. Download the repository.
2. Make a copy of the two config files removing .example from the name, and input your own params.
3. The bot is currently not daemon ready and runs in the terminal.  This means that if you would
   like it to run independent of your shell session you will need to use a tool like Screen.
4. Within the project directory run ./dankbot_run.py - the script specifies python3 - depending on
   your system you may need to change this to just python.

====
Todo
====

1. Clean up project and make ready for setuptools
2. Better config file storeage... ie. not in project directory.
3. Ability to reload config files.
4. Stop the bot posting the same kill to the same channel more than once.
5. Ability to specify an array of characters to monitor rather than just one.
