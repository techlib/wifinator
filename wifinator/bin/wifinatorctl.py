#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

import os
import sys
import click

# Configuration is stored in a boring ini file.
from configparser import ConfigParser
from collections import OrderedDict

# CSV writer for output formatting.
from csv import writer, DictWriter

# Import the Aruba driver.
from wifinator.aruba import Aruba


__all__ = ['cli']


pass_aruba = click.make_pass_decorator(Aruba)

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

    # Parse in the configuration file.
    ini = ConfigParser()
    ini.read(config)

    # Read WiFi controller options.
    aruba_address = ini.get('aruba', 'address')
    aruba_username = ini.get('aruba', 'username')
    aruba_password = ini.get('aruba', 'password')

    # Prepare the WiFi controller client.
    aruba = Aruba(aruba_address, aruba_username, aruba_password)
    aruba.login()

    # Pass the client onto the sub-commands.
    ctx.obj = aruba


@cli.command('essid-stats')
@pass_aruba
def essid_stats(aruba):
    """
    Output CSV-formatted ESSID user counts.
    """

    csv = writer(sys.stdout)

    csv.writerow(['count', 'essid'])
    for essid, count in aruba.essid_stats().items():
        csv.writerow([count, essid])

@cli.command('stations')
@pass_aruba
def stations(aruba):
    """
    Output full CSV-formatted station listing.
    """

    csv = DictWriter(sys.stdout, fieldnames=[
        'mac', 'name', 'role', 'age', 'auth', 'ap',
        'essid', 'phy', 'remote', 'profile',
    ])

    csv.writeheader()
    for station in aruba.list_stations().values():
        csv.writerow(station)


if __name__ == '__main__':
    cli()


# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-
