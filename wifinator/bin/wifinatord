#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

import os
import sys
import click

# Twisted hosts our website and helps with async development.
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource
from twisted.python import log

# Data are accessed through SQLSoup, using SQLAlchemy.
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from sqlsoup import SQLSoup

# Configuration is stored in a boring ini file.
from configparser import ConfigParser

# Import all the application handles.
from wifinator.aruba import Aruba
from wifinator.manager import Manager
from wifinator.rbac import AccessModel
from wifinator.site import make_site


__all__ = ['cli']


@click.command()
@click.option('--config', '-c', default='/etc/ntk/wifinator.ini',
              metavar='PATH', help='Load a configuration file.')

@click.option('--debug', '-d', default=False, is_flag=True,
              help='Enable debug logging.')

@click.version_option('0.1.0')
def cli(config, debug):
    """
    Run the Wifinátor site and all background tasks.
    """

    # Start Twisted logging to console.
    log.startLogging(sys.stderr)

    if not os.path.isfile(config):
        log.msg('Configuration file does not exist, exiting.')
        sys.exit(1)

    # Parse in the configuration file.
    ini = ConfigParser()
    ini.read(config)

    # Read database iniuration options.
    db_url = ini.get('database', 'url')

    # Read website iniuration options.
    http_debug = ini.getboolean('http', 'debug', fallback=False)
    http_host = ini.get('http', 'host', fallback='localhost')
    http_port = ini.getint('http', 'port', fallback=5000)

    # Read role mappings.
    access_model = AccessModel(ini.items('access'))

    # Prepare database connection with table reflection.
    engine = create_engine(db_url, isolation_level='SERIALIZABLE')
    session = scoped_session(sessionmaker(autocommit=False, autoflush=False))
    db = SQLSoup(engine, session=session)

    # Read WiFi controller options.
    aruba_address = ini.get('aruba', 'address')
    aruba_username = ini.get('aruba', 'username')
    aruba_password = ini.get('aruba', 'password')
    profile_prefix = ini.get('aruba', 'profile-prefix')

    # Prepare the WiFi controller client.
    aruba = Aruba(aruba_address, aruba_username, aruba_password)

    # Prepare the manager that runs our background tasks.
    manager = Manager(db, aruba, profile_prefix)

    # Prepare the website that will get exposed to the users.
    site = make_site(db, manager, access_model, debug=http_debug)

    # Prepare WSGI resource for the website.
    site = Site(WSGIResource(reactor, reactor.getThreadPool(), site))

    # Bind the website to it's address.
    reactor.listenTCP(http_port, site, interface=http_host)

    # Schedule a call to the manager right after we finish here.
    reactor.callLater(0, manager.start)

    # Run the Twisted reactor until the user terminates us.
    reactor.run()


if __name__ == '__main__':
    cli()


# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-
