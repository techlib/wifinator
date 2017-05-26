#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

__all__ = ['Manager']

from twisted.internet.threads import deferToThread
from twisted.internet import task, reactor
from twisted.python import log

from wifinator.aruba import Aruba, ArubaError

class Manager(object):
    def __init__(self, db, aruba, profile_prefix):
        self.db = db
        self.aruba = aruba
        self.profile_prefix = profile_prefix

    def start(self):
        """Starts periodic operations."""
        task.LoopingCall(self.schedule_sync).start(300.0)

    def sync(self, force=[]):
        """
        Synchronizes controller configuration.

        Please run asynchronously so that the web user interface won't
        get blocked during the reconfiguration.  It takes some time...

        If you pass non-empty `force` list, all SSIDs it contains will
        be updated regardless of their current status.  Used to propagate
        all changes right after the user confirms them.
        """

        log.msg('Starting synchronization...')

        # Fetch profiles that should be active right now.
        desired_profiles = self.db.bind.execute('''
            SELECT ssid, psk
            FROM profile
            WHERE tsrange(start, stop) @> now()::timestamp
        ''').fetchall()

        desired_profiles = {ssid: psk for ssid, psk in desired_profiles}

        # Log into the controller.
        self.aruba.login()

        # Fetch current profiles from controller.
        current_profiles = self.aruba.list_profiles()

        # Collect foreign SSIDs to prevent creating duplicates.
        foreign_ssids = set()

        # Remove those that do not match the designated prefix.
        for name, info in list(current_profiles.items()):
            if not name.startswith(self.profile_prefix):
                foreign_ssids.add(info['ssid'])
                del current_profiles[name]

        def edit_profile(profile, ssid, psk, active):
            log.msg('Edit {profile}: ssid={ssid}, psk={psk}, active={active}' \
                        .format(**locals()))
            return self.aruba.edit_profile(profile, ssid, psk, active)

        # Adjust existing profiles on the controller.
        for name, info in list(current_profiles.items()):
            if info['ssid'] in desired_profiles:
                if not info['active'] or info['ssid'] in force:
                    edit_profile(name, info['ssid'], desired_profiles[info['ssid']], True)

                # Profile in not free and SSID exists.
                del current_profiles[name]
                del desired_profiles[info['ssid']]

            elif info['ssid'] == name:
                if info['active']:
                    edit_profile(name, name, 'xxx', False)

            else:
                edit_profile(name, name, 'xxx', False)

        # Map desired profiles to inactive ones on the controller.
        for ssid, psk in list(desired_profiles.items()):
            # Do not assign conflicting SSIDs.
            if ssid in foreign_ssids:
                log.msg('Conflicting SSID: {0}'.format(ssid))
                continue

            # Allocate one of the current profiles.
            name = list(current_profiles.keys())[0]
            del current_profiles[name]

            # Modify it to reflect the desired configuration.
            edit_profile(name, ssid, psk, True)

        log.msg('Synchronization finished.')

    def schedule_sync(self, force=[]):
        """
        Shedule controller synchronization.

        Use freely (but not too often, it calls the controller after all),
        after you modify database profiles to speed up the synchronization.
        """
        deferToThread(self.sync, force)



# vim:set sw=4 ts=4 et:
