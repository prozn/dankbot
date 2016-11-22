#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import daemon
import argparse
import os

from dankbot.bot import main

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--nodaemon", help="Do not run in daemon mode.", action="store_true")
    parser.add_argument("--config", help="Specify path to folder containing config files.")

    args = parser.parse_args()

    if args.nodaemon:
        print("Running bot in the terminal.")
        if args.config:
            print("Configuration path specified: %s" % os.path.abspath(args.config))
            main(os.path.abspath(args.config))
        else:
            main()
    else:
        print("Running bot in daemon mode.")
        with daemon.DaemonContext():
            if args.config:
                print("Configuration path specified: %s" % os.path.abspath(args.config))
                main(os.path.abspath(args.config))
            else:
                main()
