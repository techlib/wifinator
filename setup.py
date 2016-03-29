#!/usr/bin/python3 -tt

from setuptools import setup
import os.path

setup(
    name = 'wifinator',
    version = '1',
    author = 'NTK',
    description = ('Aruba Ad-Hoc WiFi Configuration Tool'),
    license = 'MIT',
    keywords = 'aruba wifi adhoc configuration',
    url = 'http://github.com/techlib/wifinator',
    include_package_data = True,
    package_data = {
        '': ['*.png', '*.js', '*.html'],
    },
    packages = [
        'wifinator',
    ],
    classifiers = [
        'License :: OSI Approved :: MIT License',
    ],
    scripts = ['wifinator-daemon', 'wifinator-stats']
)


# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-
