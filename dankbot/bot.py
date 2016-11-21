import time
import requests
import configparser

from slackclient import SlackClient

config = configparser.SafeConfigParser()
config.read("config.ini")

searches = configparser.SafeConfigParser()
searches.read("searches.ini")

SLACK_API_TOKEN = config.get('slack', 'slack_api_token')
sc = SlackClient(SLACK_API_TOKEN)


def main():
    while True:
        if getRedisq():
            time.sleep(0.5)
        else:
            time.sleep(5)


def getRedisq():
    try:
        r = requests.get('https://redisq.zkillboard.com/listen.php')
        response = r.json()
        if response.get('package') is None:
            print('No killmail received.')
        else:
            cycleChannels(prepareKillmail(response.get('package')))
        return True
    except Exception:
        print("Error occurred calling zkill rdisq")
        return False


def prepareKillmail(package):
    attackerList = []
    for attacker in package.get('killmail', {}).get('attackers', {}):
        att = {
            'character': attacker.get('character', {}).get('id_str'),
            'name': attacker.get('character', {}).get('name'),
            'corporation': attacker.get('corporation', {}).get('id_str'),
            'corpName': attacker.get('corporation', {}).get('name'),
            'alliance': attacker.get('alliance', {}).get('id_str'),
            'allianceName': attacker.get('alliance', {}).get('name'),
            'ship': attacker.get('shipType', {}).get('id_str'),
            'shipName': attacker.get('shipType', {}).get('name')
        }
        if att['corporation'] not in (None, "0"):
            attackerList.append(att)

        if attacker.get('finalBlow') is True:
            finalBlow = att

        del att

    if len(attackerList) == 0:
        attackerList.append(finalBlow)

    cleanMail = {
        'id': package.get('killID'),
        'solo': True if len(attackerList) == 1 else False,
        'victim': {
            'character': package.get('killmail', {}).get('victim', {}).get('character', {}).get('id_str'),
            'name': package.get('killmail', {}).get('victim', {}).get('character', {}).get('name'),
            'corporation': package.get('killmail', {}).get('victim', {}).get('corporation', {}).get('id_str'),
            'alliance': package.get('killmail', {}).get('victim', {}).get('alliance', {}).get('id_str'),
            'ship': package.get('killmail', {}).get('victim', {}).get('shipType', {}).get('id_str'),
            'shipName': package.get('killmail', {}).get('victim', {}).get('shipType', {}).get('name')
        },
        'value': package.get('zkb', {}).get('totalValue'),
        'attackers': attackerList,
        'finalBlow': finalBlow
    }
    return cleanMail


def cycleChannels(km):
    for channel in searches.sections():
        print("Searching channel %s" % channel)
        if searches.getboolean(channel, 'include_capsules') is False and \
                km['victim']['ship'] in config.get('killboard', 'capsule_type_ids').split(','):
            print("Kill is a pod and pods are ignored by config.")
            continue

        if km['victim']['ship'] in config.get('killboard', 'capsule_type_ids').split(',') and \
                km['value'] < searches.getfloat(channel, 'minimum_capsule_value'):
            print("Kill is a pod and value is below minimum capsule value in config.")
            continue

        if any(a[searches.get(channel, 'zkill_search_type')]
                in searches.get(channel, 'zkill_search_id').split(',') for a in km['attackers']):
            if km['solo'] is True:
                sendKill('solo', channel, km)
                continue

            if km['value'] >= searches.getfloat(channel, 'expensive_kill_limit'):
                sendKill('expensive', channel, km)
                continue

            print("Matching kill found for channel (%s) but it was not solo or expsneive" % channel)


def sendKill(type, searchsection, km):
    if type == "expensive":
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
    elif type == "solo":
        fields = [
            {
                'title': 'Killer',
                'value': km['finalBlow']['name'],
                'short': True
            },
            {
                'title': 'Using',
                'value': km['finalBlow']['shipName'],
                'short': True
            }
        ]

    attachment_payload = [{
        'fallback': 'Alert!!! %s died in a %s worth %s -- %s%s' % (
            km['victim']['name'], km['victim']['shipName'], "{:,.0f}".format(km['value']),
            config.get('killboard', 'kill_url'), km['id']),
        'color': 'danger',
        'title': '%s died in a %s worth %s ISK' % (km['victim']['name'], km['victim']['shipName'],
                                                   "{:,.0f}".format(km['value'])),
        'title_link': '%s%s' % (config.get('killboard', 'kill_url'), km['id']),
        'fields': fields,
        'thumb_url': '%s%s_256.png' % (config.get('killboard', 'ship_renders'), km['victim']['ship'])
    }]

    sc.api_call(
        "chat.postMessage",
        as_user="false",
        username=config.get('slack', 'slack_bot_name'),
        channel=searches.get(searchsection, 'channel_name'),
        icon_emoji=config.get('slack', 'slack_bot_icon'),
        attachments=attachment_payload,
        text="*Solo Kill!!!*" if km['solo'] else "*Dank Frag!!!*"
    )
    print("Kill sent to slack...")


if __name__ == '__main__':
    main()
