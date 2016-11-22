#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import daemon
import argparse

from dankbot.bot import main

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodaemon", help="Do not run in daemon mode.", action="store_true")
    args = parser.parse_args()
    if args.nodaemon:
        print("Running bot in the terminal.")
        main()
    else:
        print("Running bot in daemon mode.")
        with daemon.DaemonContext():
            main()
