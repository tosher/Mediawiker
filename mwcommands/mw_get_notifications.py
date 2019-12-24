#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

from datetime import datetime
import webbrowser
# import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerNotificationsCommand(sublime_plugin.WindowCommand):
    '''
    https://www.mediawiki.org/wiki/Notifications
    https://www.mediawiki.org/wiki/Extension:Echo
    '''

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')

    def run(self):
        ignore_read = not utils.props.get_setting('notifications_show_all')
        read_sign = utils.props.get_setting('notifications_read_sign')
        self.msgs = utils.api.get_notifications_list(ignore_read=ignore_read)
        self.msgs = sorted(self.msgs, key=lambda k: (k['read'], -k['timestamp']))
        n_list = ['All in browser']
        print(self.msgs)
        for m in self.msgs:
            print(m['timestamp'])
            line = '{}, {}: ({}) at {} {}'.format(
                m['title'],
                m['agent'],
                m['type'],
                datetime.fromtimestamp(m['timestamp']),
                ' {}'.format(read_sign) if m['read'] else ''
            )
            n_list.append(line)

        self.window.show_quick_panel(n_list, self.on_done)

    def on_done(self, idx):
        if idx > -1:
            if idx == 0:
                url = utils.get_page_url(page_name='Special:Notifications')
                webbrowser.open(url)
            else:
                title = self.msgs[idx - 1].get('title', None)
                if title:
                    self.window.run_command(utils.cmd('page'), {
                        "action": utils.cmd('show_page'),
                        'action_params': {"title": title},
                        "check_notifications": False
                    })
