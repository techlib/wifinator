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

# Import the Aruba driver.
from wifinator.aruba import Aruba


__all__ = ['cli']


class Model:
    def __init__(self, config):
        # Parse in the configuration file.
        ini = ConfigParser()
        ini.read(config)

        # Read WiFi controller options.
        aruba_address = ini.get('aruba', 'address')
        aruba_username = ini.get('aruba', 'username')
        aruba_password = ini.get('aruba', 'password')

        # Prepare the WiFi controller client.
        self.aruba = Aruba(aruba_address, aruba_username, aruba_password)

        # Parse in the affiliation mapping rules.
        self.affiliation = OrderedDict()

        for org, rules in ini.items('affiliation'):
            self.affiliation[org] = re.split(r'\s+', rules)

    def get_affiliation(self, name):
        if '@' not in name:
            return 'Local'

        user, domain = name.split('@', 1)

        for org, rules in self.affiliation.items():
            for rule in rules:
                if fnmatch(domain, rule):
                    return org

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

    headers = {
        'mac': 'MAC',
        'name': 'Name',
        'role': 'Role',
        'age': 'Age',
        'auth': 'Auth',
        'ap': 'AP',
        'essid': 'ESSID',
        'phy': 'Phy',
        'remote': 'Remote',
        'profile': 'Profile',
    }

    rows = list(model.aruba.list_stations().values())
    print_table(headers, rows, csv)

@cli.command('essid-stats')
@click.option('--csv', '-C', is_flag=True, help='Format output as CSV.')
@pass_model
def essid_stats(model, csv=False):
    """
    ESSID user counts
    """

    rows = model.aruba.essid_stats().items()
    print_table(('ESSID', 'Count'), rows, csv)

@cli.command('org-users')
@click.option('--csv', '-C', is_flag=True, help='Format output as CSV.')
@pass_model
def user_domains(model, csv=False):
    """
    Organization user counts
    """

    orgs = {}

    for station in model.aruba.list_stations().values():
        org = model.get_affiliation(station['name'])
        orgs.setdefault(org, 0)
        orgs[org] += 1

    print_table(('Organization', 'Count'), orgs.items(), csv)

def print_table(headers, rows, csv=False):
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


if __name__ == '__main__':
    cli()


# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-
