#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import time
import requests
import configparser
import logging
import logging.handlers
from esipy import App
from esipy import EsiClient

from slackclient import SlackClient

logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

config = configparser.SafeConfigParser()
searches = configparser.SafeConfigParser()
sc = None


def main(configpath="."):

    global sc

    config.read("%s/config.ini" % configpath)
    searches.read("%s/searches.ini" % configpath)

    sc = SlackClient(config.get('slack', 'slack_api_token'))
    swagger = App.create(url="https://esi.tech.ccp.is/latest/swagger.json?datasource=tranquility")

    esi = EsiClient(
        retry_requests=True,  # set to retry on http 5xx error (default False)
        header={'User-Agent': 'Killmail Slack Bot by Prozn https://github.com/prozn/dankbot/'}
    )

    while True:
        if getRedisq():
            time.sleep(0.5)
        else:
            time.sleep(5)


def getRedisq():
    try:
        r = requests.get('https://redisq.zkillboard.com/listen.php')
        response = r.json()
    except Exception:
        logger.warning("Error occurred calling zkill redisq")
        return False
    if response.get('package') is None:
        logger.debug('No killmail received.')
    else:
        cycleChannels(prepareKillmail(response.get('package')))
    return True


def prepareKillmail(package):
    attackerList = []
    for attacker in package.get('killmail', {}).get('attackers', {}):
        att = {
            'character': attacker.get('character_id', 0),
            'corporation': attacker.get('corporation_id', 0),
            'alliance': attacker.get('alliance_id', 0),
            'ship': attacker.get('ship_type_id', 0),
        }
        if att['corporation'] not in (None, "0", 0):
            attackerList.append(att)

        if attacker.get('final_blow') is True:
            finalBlow = att

        del att

    if len(attackerList) == 0:
        attackerList.append(finalBlow)

    cleanMail = {
        'id': package.get('killID'),
        'solo': True if len(attackerList) == 1 else False,
        'victim': {
            'character': package.get('killmail', {}).get('victim', {}).get('character_id', 0),
            'corporation': package.get('killmail', {}).get('victim', {}).get('corporation_id', 0),
            'alliance': package.get('killmail', {}).get('victim', {}).get('alliance_id', 0),
            'ship': package.get('killmail', {}).get('victim', {}).get('ship_type_id', 0),
        },
        'location': {
            'id': package.get('killmail', {}).get('solar_system_id', 0),
        },
        'value': package.get('zkb', {}).get('totalValue'),
        'attackers': attackerList,
        'finalBlow': finalBlow
    }
    return cleanMail


def cycleChannels(km):
    sentchannels = []
    for channel in searches.sections():
        logger.debug("Searching channel %s" % channel)
        if searches.get(channel, 'channel_name') in sentchannels:
            logger.debug("Killmail has already been sent to channel %s, skipping."
                         % searches.get(channel, 'channel_name'))
            continue

        if searches.getboolean(channel, 'include_capsules') is False and \
                km['victim']['ship'] in config.get('killboard', 'capsule_type_ids').split(','):
            logger.debug("Kill is a pod and pods are ignored by config.")
            continue

        if km['victim']['ship'] in config.get('killboard', 'capsule_type_ids').split(',') and \
                km['value'] < searches.getfloat(channel, 'minimum_capsule_value'):
            logger.debug("Kill is a pod and value is below minimum capsule value in config.")
            continue

        if any(a[searches.get(channel, 'zkill_search_type')]
                in searches.get(channel, 'zkill_search_id').split(',') for a in km['attackers']):
            if km['solo'] is True:
                sendKill('solo', channel, km)
                sentchannels.append(searches.get(channel, 'channel_name'))
                continue

            if km['value'] >= searches.getfloat(channel, 'expensive_kill_limit'):
                sendKill('expensive', channel, km)
                continue

            logger.debug("Matching kill found for channel (%s) but it was not solo or expsneive" % channel)

        if searches.getboolean(channel, 'post_losses') and \
                km['victim'][searches.get(channel, 'zkill_search_type')] == searches.get(channel, 'zkill_search_id'):
            if km['victim']['ship'] in searches.get(channel, 'loss_ship_type_ids'):
                sendKill('loss_ship', channel, km)
                continue
            try:
                if searches.getboolean(channel, 'loss_value') is False:
                    pass
                else:
                    logger.warning("Loss value config param evaluated to True"
                                   " - permitted settings are False or numerical")
                    pass
            except ValueError:
                if km['value'] >= searches.getfloat(channel, 'loss_value'):
                    sendKill('loss_expensive', channel, km)
                    continue

        if km['victim']['ship'] in config.get('killboard', 'super_type_ids').split(',') and \
                searches.getboolean(channel, 'post_all_super_kills'):
            sendKill('super', channel, km)
            continue


def fluffKillmail(km):
    # Call ESI API and add:
    # For victim, attackers, finalBlow: name, shipName
    # For victim, finalBlow: corpName, allianceName
    # For location: name
    return km


def sendKill(killtype, searchsection, km):
    km = fluffKillmail(km)
    if killtype == "expensive":
        fields = [
            {
                'title': 'Involved Players',
                'value': '\n'.join(["{name} ({shipName})".format(**a) for a in km['attackers']
                                   if a[searches.get(searchsection, 'zkill_search_type')]
                                   == searches.get(searchsection, 'zkill_search_id')]),
                'short': True
            },
            {
                'title': 'Final Blow',
                'value': "{name} ({shipName})".format(**km['finalBlow']),
                'short': True
            }
        ]
    elif killtype == "solo":
        fields = [
            {
                'title': 'Killer',
                'value': km['finalBlow'].get('name'),
                'short': True
            },
            {
                'title': 'Using',
                'value': km['finalBlow'].get('shipName'),
                'short': True
            }
        ]
    elif killtype == "super":
        fields = [
            {
                'title': 'Losing corp/alliance',
                'value': "%s/%s" % (km['victim'].get('corpName'), km['victim'].get('allianceName')),
                'short': True
            },
            {
                'title': 'Killer',
                'value': "%s (%s)" % (km['finalBlow'].get('name'),
                                      km['finalBlow'].get('corpName') if km['finalBlow'].get('allianceName') == "None"
                                      else km['finalBlow'].get('allianceName')),
                'short': True
            },
            {
                'title': 'Location',
                'value': km['location']['name'],
                'short': True
            }
        ]
    elif killtype in ("loss_ship", "loss_expensive"):
        fields = [
            {
                'title': 'Killer',
                'value': "%s (%s)" % (km['finalBlow'].get('name'),
                                      km['finalBlow'].get('corpName') if km['finalBlow'].get('allianceName') == "None"
                                      else km['finalBlow'].get('allianceName')),
                'short': True
            },
            {
                'title': 'Using',
                'value': km['finalBlow'].get('shipName'),
                'short': True
            }
        ]

    attachment_payload = {
        'fallback': 'Alert!!! %s died in a %s worth %s -- %s%s' % (
            km['victim']['name'], km['victim']['shipName'], "{:,.0f}".format(km['value']),
            config.get('killboard', 'kill_url'), km['id']),
        'color': 'danger' if killtype != 'super' else 'warning',
        'pretext': "*Solo Kill!!!*" if killtype == "solo"
        else "*No scrubs... no poors...*" if killtype[:4] == "loss" else "*Dank Frag!!!*",
        'title': '%s died in a %s worth %s ISK' % (km['victim']['name'], km['victim']['shipName'],
                                                   "{:,.0f}".format(km['value'])),
        'title_link': '%s%s' % (config.get('killboard', 'kill_url'), km['id']),
        'fields': fields,
        'thumb_url': '%s%s_256.png' % (config.get('killboard', 'ship_renders'), km['victim']['ship']),
        'mrkdwn_in': ['pretext']
    }

    if killtype == "super":
        attachment_payload.update({'footer': 'This is a generic super kill.'})

    sc.api_call(
        "chat.postMessage",
        as_user="false",
        username=config.get('slack', 'slack_bot_name'),
        channel=searches.get(searchsection, 'channel_name'),
        icon_emoji=config.get('slack', 'slack_bot_icon'),
        attachments=[attachment_payload]
    )
    logger.info("Kill sent to slack...")


def checkConfigFiles(path):
    # implement config file checks
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--nodaemon", help="Do not run in daemon mode", action="store_true")
    parser.add_argument("--config", help="Specify path to folder containing config files")
    parser.add_argument("--forcelogfile", help="Force the bot to write to logfiles when not running in daemon mode",
                        action="store_true")
    parser.add_argument("--debug", help="Log/show debugging messages", action="store_true")
    parser.add_argument("--nologging", help="Do not log anything", action="store_true")
    parser.add_argument("--logfile", help="Specify custom log file path")

    args = parser.parse_args()

    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.DEBUG)

    if args.logfile:
        logfilename = os.path.abspath(args.logfile)
    else:
        logdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs")
        if not os.path.exists(logdir):
            os.mkdir(logdir)
        logfilename = os.path.join(logdir, "dankbot.log")
    logfile = logging.handlers.RotatingFileHandler(logfilename, maxBytes=10000000, backupCount=5)
    logfile.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    if args.debug:
        logfile.setLevel(logging.DEBUG)
        console.setLevel(logging.DEBUG)
    else:
        logfile.setLevel(logging.INFO)
        console.setLevel(logging.INFO)

    if args.nodaemon and not args.nologging:
        logger.addHandler(console)

    if not args.nologging:
        if not args.nodaemon or args.forcelogfile:
            logger.debug("Logging to %s" % logfilename)
            logger.addHandler(logfile)

    if args.config:
        configpath = os.path.abspath(args.config)
        logger.info("Configuration path specified: %s" % configpath)
    else:
        configpath = os.path.abspath(".")
        logger.info("Using default config path: %s" % configpath)

    if checkConfigFiles(configpath):
        if args.nodaemon:
            logger.info("Running bot in the terminal...")
            main(configpath)
        else:
            logger.info("Running bot in daemon mode...")
            import daemon
            with daemon.DaemonContext():
                main(configpath)
    else:
        logger.critical("Config files did not pass validation checks, exiting...")
        exit()
