#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import daemon

from dankbot.bot import main

if __name__ == '__main__':
    with daemon.DaemonContext():
        main()
