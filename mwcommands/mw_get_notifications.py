#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import webbrowser

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerNotificationsCommand(sublime_plugin.WindowCommand):
    ''' alias to GetNotifications command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_get_notifications"})


class MediawikerGetNotificationsCommand(sublime_plugin.TextCommand):
    '''
    https://www.mediawiki.org/wiki/Notifications
    https://www.mediawiki.org/wiki/Extension:Echo
    NOTE: Beta
    '''

    def run(self, edit, title, password):
        notifications_type = mw.get_setting('mediawiki_notifications_show_all', True)
        self.read_sign = mw.get_setting('mediawiki_notifications_read_sign', ' [+]')
        sitecon = mw.get_connect(password)
        ns = sitecon.notifications()
        self.msgs = []
        if ns:
            if isinstance(ns, dict):
                for n in ns.keys():
                    msg = ns.get(n, {})
                    msg_read = msg.get('read', '')
                    if notifications_type or not msg_read:
                        self.msgs.append(self._get_data(msg))
            elif isinstance(ns, list):
                for msg in ns:
                    msg_read = msg.get('read', '')
                    if notifications_type or not msg_read:
                        self.msgs.append(self._get_data(msg))

        self.msgs = sorted(self.msgs, key=lambda k: k['read'])
        n_list = ['All in browser'] + ['%s, %s: %s (%s)%s' % (m['title'], m['agent'], m['timestamp'], m['type'], m['read']) for m in self.msgs]
        sublime.active_window().show_quick_panel(n_list, self.on_done)

    def _get_data(self, msg):
        _ = {}
        _['title'] = msg.get('title', {}).get('full')
        _['type'] = msg.get('type', None)
        _['timestamp'] = msg.get('timestamp', {}).get('date', None)
        _['agent'] = msg.get('agent', {}).get('name', None)
        _['read'] = self.read_sign if msg.get('read', None) else ''
        return _

    def on_done(self, idx):
        if idx > -1:
            if idx == 0:
                url = mw.get_page_url(page_name='Special:Notifications')
                webbrowser.open(url)
            else:
                title = self.msgs[idx - 1].get('title', None)
                if title:
                    sublime.active_window().run_command("mediawiker_page", {
                        "title": title,
                        "action": "mediawiker_show_page",
                        "check_notifications": False})
