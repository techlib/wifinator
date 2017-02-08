#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

from threading import Lock
from requests import Session, HTTPError
from time import time
from xml.etree.ElementTree import XML, ParseError

from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.packages.urllib3 import disable_warnings

disable_warnings(InsecureRequestWarning)

class ArubaError(Exception):
    """Generic error related to communication with Aruba WiFi controllers."""

class Aruba(object):
    # <url> ? command @@ timestamp & UIDARUBA=session-id
    COMMAND_URL = 'https://{host}:4343/screens/cmnutil/execCommandReturnResult.xml'

    # POST opcode, url, needxml, uid, passwd
    LOGIN_URL = 'https://{host}:4343/screens/wms/wms.login'

    def __init__(self, host, username, password):
        """Store address and credentials for later."""

        self.host = host
        self.username = username
        self.password = password

        self.session = Session()

        self.login_url = self.LOGIN_URL.format(host=host)
        self.command_url = self.COMMAND_URL.format(host=host)

    def request(self, command):
        s = self.session.cookies.get('SESSION', '')
        p = '{0}@@{1}&UIDARUBA={2}'.format(command, int(time()), s)
        r = self.session.get(self.command_url, verify=False, params=p)
        return r.text

    def request_table(self, command):
        try:
            r = XML(self.request(command))
        except ParseError:
            raise ArubaError('Response is not a valid XML element')

        if r.find('t') is None:
            raise ArubaError('Response does not contain a table')

        return [[(c.text.strip() if c.text is not None else '') for c in row] \
                for row in r.find('t')[1:]]

    def request_dict(self, command):
        return {row[0]: row[1] for row in self.request_table(command)}

    def login(self):
        if XML(self.request('show roleinfo')).find('data'):
            return

        r = self.session.post(self.login_url, verify=False, data={
            'opcode': 'login',
            'url': '/',
            'needxml': '0',
            'uid': self.username,
            'passwd': self.password,
        })

        if 'Authentication complete' not in r.text:
            raise ArubaError('Login failed')

    def list_profiles(self):
        """List service profiles with SSID and Beacon settings."""

        profiles = {}

        for name in self.request_dict('show wlan ssid-profile'):
            detail = self.request_dict('show wlan ssid-profile ' + name)
            profiles[name] = {
                    'ssid': detail['ESSID'],
                    'active': detail['SSID enable'] == 'Enabled',
            }

        return profiles

    def list_stations(self):
        """List client stations with MAC addresses and more."""

        stations = {}

        r = self.request_table('show station-table')
        for mac, name, role, age, auth, ap, essid, phy, remote, profile in r:
            stations[mac] = {
                'mac': mac,
                'name': name,
                'role': role,
                'age': age,
                'auth': auth,
                'ap': ap,
                'essid': essid,
                'phy': phy,
                'remote': remote,
                'profile': profile,
            }

        return stations

    def essid_stats(self):
        stats = {}

        for station in self.list_stations().values():
            essid = station['essid']
            stats.setdefault(essid, 0)
            stats[essid] += 1

        return stats

    def ap_stats(self):
        stats = {}

        for station in self.list_stations().values():
            ap = station['ap']
            stats.setdefault(ap, 0)
            stats[ap] += 1

        return stats

    def edit_profile(self, profile, ssid, psk, active):
        """Adjust service profile. PSK is in plain text."""

        self.request('wlan ssid-profile {0} essid {1}'.format(profile, ssid))
        self.request('wlan ssid-profile {0} wpa-passphrase {1}'.format(profile, psk))

        if active:
            self.request('wlan ssid-profile {0} ssid-enable'.format(profile))
        else:
            self.request('wlan ssid-profile {0} no ssid-enable'.format(profile))


# vim:set sw=4 ts=4 et:
