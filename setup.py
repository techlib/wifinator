#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from os.path import *

def read_requires(path=None):
    if path is None:
        path = join(dirname(__file__), 'requirements.txt')
        print(path)

    with open(path) as fp:
        return [l.strip() for l in fp.readlines()]

setup(**{
    'name': 'wifinator',
    'version': '0.1.0',
    'author': 'NTK',
    'description': ('Aruba Ad-Hoc WiFi Configuration Tool'),
    'license': 'MIT',
    'keywords': 'aruba wifi adhoc configuration',
    'url': 'http://github.com/techlib/wifinator/',
    'include_package_data': True,
    'packages': find_packages(),
    'classifiers': [
        'License :: OSI Approved :: MIT License',
    ],
    'entry_points': '''
        [console_scripts]
        wifinatorctl=wifinator.bin.wifinatorctl:cli
        wifinatord=wifinator.bin.wifinatord:cli
    ''',
    'install_requires': read_requires(),
    'zip_safe': False,
})


# vim:set sw=4 ts=4 et:
