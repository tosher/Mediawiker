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
    '''
    https://www.mediawiki.org/wiki/Notifications
    https://www.mediawiki.org/wiki/Extension:Echo
    '''

    def run(self):
        ignore_read = not mw.get_setting('notifications_show_all')
        read_sign = mw.get_setting('notifications_read_sign')
        self.msgs = mw.api.get_notifications_list(ignore_read=ignore_read)
        self.msgs = sorted(self.msgs, key=lambda k: k['read'])
        n_list = ['All in browser']
        for m in self.msgs:
            line = '%s, %s: %s (%s)%s' % (
                m['title'],
                m['agent'],
                m['timestamp'],
                m['type'],
                ' %s' % read_sign if m['read'] else ''
            )
            n_list.append(line)

        self.window.show_quick_panel(n_list, self.on_done)

    def on_done(self, idx):
        if idx > -1:
            if idx == 0:
                url = mw.get_page_url(page_name='Special:Notifications')
                webbrowser.open(url)
            else:
                title = self.msgs[idx - 1].get('title', None)
                if title:
                    self.window.run_command(mw.cmd('page'), {
                        "action": mw.cmd('show_page'),
                        'action_params': {"title": title},
                        "check_notifications": False
                    })
