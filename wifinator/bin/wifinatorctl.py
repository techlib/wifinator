#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

import re
import os
import sys
import click

# Configuration is stored in a boring ini file.
from configparser import ConfigParser
from collections import OrderedDict

# Output formatting libraries.
from csv import writer, DictWriter
from tabulate import tabulate

# For affiliation rule parsing.
from fnmatch import fnmatch

from ldap3 import Server, Connection, ALL

# Import the Aruba driver.
from wifinator.aruba import Aruba


__all__ = ['cli']


class Model:
    def __init__(self, config):
        # Parse in the configuration file.
        ini = ConfigParser()
        ini.read(config)

        # Save the configuration for later.
        self.ini = ini

        # Read WiFi controller options.
        aruba_address = ini.get('aruba', 'address')
        aruba_username = ini.get('aruba', 'username')
        aruba_password = ini.get('aruba', 'password')

        # No LDAP connection by default.
        self.ldap = None

        # Prepare the WiFi controller client.
        self.aruba = Aruba(aruba_address, aruba_username, aruba_password)

        # Parse in the affiliation mapping rules.
        self.affiliation = OrderedDict()

        for org, rules in ini.items('affiliation'):
            self.affiliation[org] = re.split(r'\s+', rules)

    def enable_ldap(self):
        if self.ldap is not None:
            return

        ldap_host = self.ini.get('ldap', 'host')
        ldap_bind = self.ini.get('ldap', 'bind')
        ldap_pass = self.ini.get('ldap', 'pass')

        self.ldap_base = self.ini.get('ldap', 'base')
        self.ldap_filter = self.ini.get('ldap', 'filter')
        self.ldap_attribute = self.ini.get('ldap', 'attribute')

        server = Server(ldap_host, get_info=ALL)
        self.ldap = Connection(server, ldap_bind, ldap_pass, auto_bind=True)

    def ldap_search(self, name):
        if self.ldap is None:
            return

        self.ldap.search(self.ldap_base, self.ldap_filter.format(name=name),
                         attributes=[self.ldap_attribute])

        if len(self.ldap.entries) > 0:
            attr = getattr(self.ldap.entries[0], self.ldap_attribute)

            if attr is not None and len(attr) > 0:
                return attr[0]

    def get_affiliation(self, name, essid):
        if '@' in name:
            user, domain = name.split('@', 1)
        else:
            domain = self.ldap_search(name)

        for org, rules in self.affiliation.items():
            for rule in rules:
                if domain is not None and fnmatch(domain, rule):
                    return org

                if fnmatch(essid, rule):
                    return org

        if domain is None:
            return 'Local'

        return 'Other'


pass_model = click.make_pass_decorator(Model)

@click.group()
@click.option('--config', '-c', default='/etc/ntk/wifinator.ini',
              metavar='PATH', help='Load a configuration file.')

@click.version_option('0.1.0')
@click.pass_context
def cli(ctx, config):
    """
    Wifinátor command-line client utility.

    Can be used to query the Wifi controller to obtain information about
    connected devices and their users.
    """

    if not os.path.isfile(config):
        print('Configuration file does not exist, exiting.', file=sys.stderr)
        sys.exit(1)

    # Prepare the domain model.
    model = Model(config)
    model.aruba.login()

    # Pass the our model onto the sub-commands.
    ctx.obj = model

@cli.command('stations')
@click.option('--csv', '-C', is_flag=True, help='Format output as CSV.')
@pass_model
def stations(model, csv=False):
    """
    Full station listing
    """

    headers = OrderedDict([
        ('mac', 'MAC'),
        ('name', 'Name'),
        ('role', 'Role'),
        ('age', 'Age'),
        ('auth', 'Auth'),
        ('ap', 'AP'),
        ('essid', 'ESSID'),
        ('phy', 'Phy'),
        ('remote', 'Remote'),
        ('profile', 'Profile'),
    ])

    rows = list(model.aruba.list_stations().values())
    print_table(headers, rows, csv)

@cli.command('essid-stats')
@click.option('--csv', '-C', is_flag=True, help='Format output as CSV.')
@pass_model
def essid_stats(model, csv=False):
    """
    ESSID device counts
    """

    rows = model.aruba.essid_stats().items()
    print_table(('ESSID', 'Count'), sorted(rows), csv)

@cli.command('org-users')
@click.option('--csv', '-C', is_flag=True, help='Format output as CSV.')
@click.option('--ldap', '-l', is_flag=True, help='Use LDAP to match logins.')
@pass_model
def user_domains(model, csv=False, ldap=False):
    """
    Organization user counts

    If the LDAP lookup is enabled, all users without a known domain to be
    used to detect their affiliation will be looked up using LDAP and the
    configured attribute will be used instead.
    """

    if ldap:
        model.enable_ldap()

    orgs = {}
    seen = set()

    for station in model.aruba.list_stations().values():
        # Make sure we do not count the same user multiple times.
        # Yes, they can have multiple devices.

        if station['name'] in seen:
            continue

        seen.add(station['name'])

        org = model.get_affiliation(station['name'], station['essid'])
        orgs.setdefault(org, 0)
        orgs[org] += 1

    print_table(('Organization', 'Count'), sorted(orgs.items()), csv)

def print_table(headers, rows, csv=False):
    if isinstance(headers, dict):
        rows = reorder_rows_by_headers(headers, rows)

    if csv:
        if isinstance(headers, dict):
            w = DictWriter(sys.stdout, dialect='unix',
                           fieldnames=[h.lower() for h in headers])

            w.writeheader()

            for row in rows:
                w.writerow({k.lower(): v for k, v in row.items()})

        else:
            w = writer(sys.stdout, dialect='unix')
            w.writerow([h.lower() for h in headers])

            for row in rows:
                w.writerow(row)

    else:
        print(tabulate(rows, headers))

def reorder_rows_by_headers(headers, rows):
    new_rows = []

    for row in rows:
        new_row = OrderedDict()

        for header in headers:
            new_row[header] = row[header]

        new_rows.append(new_row)

    return new_rows


if __name__ == '__main__':
    cli()


# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-
