#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerPageCommand(sublime_plugin.WindowCommand):
    '''prepare all actions with wiki'''

    check_notifications = True

    def run(self, action, action_params=None, **kwargs):
        self.action = action
        self.action_params = action_params
        self.check_notifications = kwargs.get('check_notifications', self.check_notifications)

        if not mw.conman.require_password():
            panel_passwd = mw.InputPanelPassword(callback=self.command_run)
            panel_passwd.get_password()
        else:
            mw.set_timeout_async(self.command_run, 0)

    def command_run(self):

        self.window.active_view().run_command(self.action, self.action_params)
        try:
            self.get_notifications()
        except Exception as e:
            mw.status_message('Mediawiker notifications exception: %s' % e)

    def get_notifications(self):
        # check notifications on page open command
        if self.action == mw.cmd('show_page') and self.check_notifications:
            ns = mw.api.call('get_notifications')
            is_notify_exists = False
            if ns:
                # TODO: move to PreAPI
                if isinstance(ns, dict):
                    for n in ns.keys():
                        msg = ns.get(n, {})
                        msg_read = msg.get('read', None)
                        if not msg_read:
                            is_notify_exists = True
                            break
                elif isinstance(ns, list):
                    for msg in ns:
                        msg_read = msg.get('read', None)
                        if not msg_read:
                            is_notify_exists = True
                            break
            if is_notify_exists and sublime.ok_cancel_dialog('You have new notifications.'):
                self.window.run_command(mw.cmd('get_notifications'))
