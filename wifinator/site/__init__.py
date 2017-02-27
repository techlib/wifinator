#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

__all__ = ['make_site']

from sqlalchemy import *
from sqlalchemy.exc import *
from werkzeug.exceptions import *
from wifinator.site.util import *
from functools import wraps

from flask_qrcode import QRcode
from flask_weasyprint import HTML, render_pdf

from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

import flask
import os
import re

def make_site(db, manager, access_model, debug=False):
    app = flask.Flask('.'.join(__name__.split('.')[:-1]))
    app.secret_key = os.urandom(16)
    app.debug = debug

    # Init QRCode plugin
    QRcode(app)

    @app.template_filter('to_alert')
    def category_to_alert(category):
        return {
            'warning': 'alert-warning',
            'error': 'alert-danger',
        }[category]

    @app.template_filter('to_icon')
    def category_to_icon(category):
        return {
            'warning': 'pficon-warning-triangle-o',
            'error': 'pficon-error-circle-o',
        }[category]

    def interpret_audit(audit):
        """Converts audit to description of changes."""

        changes = []

        for a in audit:
            def change(desc):
                changes.append({
                    'time': a.time,
                    'user': a.user,
                    'desc': desc,
                })

            old = a.old_data
            new = a.new_data

            if old is None:
                change('created <em>%s</em>' % escape(new['ssid']))

            elif new is None:
                change('removed <em>%s</em>' % escape(old['ssid']))

            else:
                if old['ssid'] != new['ssid']:
                    change('renamed <em>%s</em> to <em>%s</em>' \
                            % (escape(old['ssid']), escape(new['ssid'])))

                if old['psk'] != new['psk']:
                    change('changed password of <em>%s</em> to <em>%s</em>' \
                            % (escape(new['ssid']), escape(new['psk'])))

                if old['start'] != new['start']:
                    change('moved first day of <em>%s</em> to <em>%s</em>' \
                            % (escape(new['ssid']), new['start'][:10]))

                if old['stop'] != new['stop']:
                    change('moved last day of <em>%s</em> to <em>%s</em>' \
                            % (escape(new['ssid']), new['stop'][:10]))

        return changes



    def has_privilege(privilege):
        roles = flask.request.headers.get('X-Roles', '')

        if not roles or '(null)' == roles:
            roles = ['impotent']
        else:
            roles = re.findall(r'\w+', roles)

        return access_model.have_privilege(privilege, roles)

    def pass_user_info(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            uid = flask.request.headers.get('X-User-Id', '0')
            username = flask.request.headers.get('X-Full-Name', 'Someone')

            kwargs.update({
                'uid': int(uid),
                'username': username.encode('latin1').decode('utf8'),
            })

            return fn(*args, **kwargs)
        return wrapper


    def authorized_only(privilege='user'):
        def make_wrapper(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                if not has_privilege(privilege):
                    raise Forbidden('RBAC Forbidden')

                return fn(*args, **kwargs)

            return wrapper
        return make_wrapper


    @app.errorhandler(Forbidden.code)
    def unauthorized(e):
        return flask.render_template('forbidden.html')


    @app.route('/')
    @authorized_only(privilege='user')
    def index():
        nonlocal has_privilege

        profiles = manager.db.profile \
                    .filter(manager.db.profile.stop > datetime.now()) \
                    .order_by(manager.db.profile.start).all()

        audit = manager.db.audit \
                    .order_by(desc(manager.db.audit.time)) \
                    .limit(50).all()

        changes = interpret_audit(audit)

        today = date.today().strftime('%Y-%m-%d')

        return flask.render_template('main.html', **locals())

    @app.route('/delete/<int:pid>')
    @authorized_only(privilege='admin')
    @pass_user_info
    def delete(pid, uid, username):
        old = manager.db.profile.get(pid)
        if old is None:
            flask.flash('Network disappeared in the meantime.', 'warning')
            return flask.redirect('/')

        manager.db.audit.insert(**{
            'user': username,
            'profile': pid,
            'old_data': {
                'ssid': old.ssid,
                'psk': old.psk,
                'start': old.start.strftime('%Y-%m-%d %H:%M:%S'),
                'stop': old.stop.strftime('%Y-%m-%d %H:%M:%S'),
            },
            'new_data': None,
            'time': datetime.now(),
        })

        manager.db.profile.filter(manager.db.profile.id == pid).delete()

        try:
            manager.db.commit()
        except SQLAlchemyError as e:
            manager.db.rollback()
            flask.flash(e.args[0], 'error')
            return flask.redirect('/')

        manager.schedule_sync()
        return flask.redirect('/')


    @app.route('/edit/<int:pid>')
    @authorized_only(privilege='admin')
    def edit(pid):
        profile = manager.db.profile.get(pid)
        if profile is None:
            flask.flash('Network disappeared in the meantime.', 'warning')
            return flask.redirect('/')

        return flask.render_template('edit.html', **locals())

    @app.route('/printable/<int:pid>')
    @authorized_only(privilege='admin')
    def printable(pid):
        profile = manager.db.profile.get(pid)
        qr_string = "WIFI:S:%s;T:WPA;P:%s" % (profile.ssid, profile.psk)
        if profile is None:
            flask.flash('Network disappeared in the meantime.', 'warning')
            return flask.redirect('/')

        html = flask.render_template('printable.html', **locals())
        return render_pdf(HTML(string=html))


    @app.route('/edit/<int:pid>/confirm', methods=['POST'])
    @authorized_only(privilege='admin')
    @pass_user_info
    def edit_confirm(pid, uid, username):
        old = manager.db.profile.get(pid)
        if old is None:
            flask.flash('Network disappeared in the meantime.', 'warning')
            return flask.redirect('/')

        new_ssid  = flask.request.form.get('ssid',  old.ssid)
        new_psk   = flask.request.form.get('psk',   old.psk)
        new_start = flask.request.form.get('start', old.start.strftime('%Y-%m-%d'))
        new_stop  = flask.request.form.get('stop',  old.stop.strftime('%Y-%m-%d'))

        if len(new_ssid) > 30:
            flask.flash('Network name too long.', 'errot')
            return flask.redirect('/edit/%i' % pid)

        if len(new_psk) > 30:
            flask.flash('Password too long.', 'error')
            return flask.redirect('/edit/%i' % pid)

        if len(new_ssid) == 0:
            flask.flash('Network name missing.', 'error')
            return flask.redirect('/edit/%i' % pid)

        if len(new_psk) < 8:
            flask.flash('Password too short, please supply at least 8 characters.', 'error')
            return flask.redirect('/edit/%i' % pid)

        try:
            new_start = datetime.strptime(new_start, '%Y-%m-%d')
            new_stop  = datetime.strptime(new_stop,  '%Y-%m-%d') \
                        + timedelta(+1, -1)
        except ValueError:
            flask.flash('Invalid date format.', 'error')
            return flask.redirect('/edit/%i' % pid)

        if new_start > new_stop:
            flask.flash('Last day must not come before the first day.', 'error')
            return flask.redirect('/edit/%i' % pid)

        manager.db.audit.insert(**{
            'user': username,
            'profile': pid,
            'old_data': {
                'ssid': old.ssid,
                'psk': old.psk,
                'start': old.start.strftime('%Y-%m-%d %H:%M:%S'),
                'stop': old.stop.strftime('%Y-%m-%d %H:%M:%S'),
            },
            'new_data': {
                'ssid': new_ssid,
                'psk': new_psk,
                'start': new_start.strftime('%Y-%m-%d %H:%M:%S'),
                'stop': new_stop.strftime('%Y-%m-%d %H:%M:%S'),
             },
            'time': datetime.now(),
        })

        old.ssid  = new_ssid
        old.psk   = new_psk
        old.start = new_start
        old.stop  = new_stop

        try:
            manager.db.commit()
        except SQLAlchemyError as e:
            manager.db.rollback()
            flask.flash(e.args[0], 'error')
            return flask.redirect('/')

        manager.schedule_sync([new_ssid])
        return flask.redirect('/')

    @app.route('/create', methods=['POST'])
    @authorized_only(privilege='admin')
    @pass_user_info
    def create(uid, username):
        ssid  = flask.request.form.get('ssid',  '')
        psk   = flask.request.form.get('psk',   '')
        start = flask.request.form.get('start', datetime.now().strftime('%Y-%m-%d'))
        stop  = flask.request.form.get('stop',  datetime.now().strftime('%Y-%m-%d'))

        if len(ssid) > 30:
            flask.flash('Network name too long.', 'error')
            return flask.redirect('/')

        if len(psk) > 30:
            flask.flash('Password too long.', 'error')
            return flask.redirect('/')

        if len(ssid) == 0:
            flask.flash('Network name missing.', 'error')
            return flask.redirect('/')

        if len(psk) < 8:
            flask.flash('Password too short, please supply at least 8 characters.', 'error')
            return flask.redirect('/')

        try:
            start = datetime.strptime(start, '%Y-%m-%d')
            stop  = datetime.strptime(stop,  '%Y-%m-%d') \
                        + timedelta(+1, -1)
        except ValueError:
            flask.flash('Invalid date format.', 'error')
            return flask.redirect('/')

        if start > stop:
            flask.flash('Last day must not come before the first day.', 'error')
            return flask.redirect('/')

        new = manager.db.profile.insert(**{
            'ssid': ssid,
            'psk': psk,
            'start': start,
            'stop': stop,
        })

        manager.db.audit.insert(**{
            'user': username,
            'profile': new.id,
            'old_data': None,
            'new_data': {
                'ssid': ssid,
                'psk': psk,
                'start': start.strftime('%Y-%m-%d %H:%M:%S'),
                'stop': stop.strftime('%Y-%m-%d %H:%M:%S'),
             },
            'time': datetime.now(),
        })

        try:
            manager.db.commit()
        except SQLAlchemyError as e:
            manager.db.rollback()
            flask.flash(e.args[0], 'error')
            return flask.redirect('/')

        manager.schedule_sync()
        return flask.redirect('/')

    @app.route('/stations', methods=['GET'])
    def stations():
        aps = {}
        for item in manager.db.location.all():
            aps[item.ap] = item.location

        stations = manager.aruba.list_stations()
        for key in stations:
            stations[key]['location'] = aps.get(stations[key]['ap'], 'Unknown')

        counts = {}
        for key, value in stations.items():
            counts[value['location']] = counts.get(value['location'], 0) + 1

        return flask.jsonify(counts)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        manager.db.rollback()


    return app


# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-
