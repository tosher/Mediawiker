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

    run_in_new_window = False
    title = None
    check_notifications = True

    def run(self, action, title='', site_active=None, action_params=None, **kwargs):
        self.site_active = site_active
        self.action = action
        self.action_params = action_params
        self.check_notifications = kwargs.get('check_notifications', True)
        self.kwargs = kwargs

        if self.action == 'mediawiker_show_page':
            panel = mw.InputPanelPageTitle()
            panel.on_done = self.on_done
            panel.get_title(title)
        else:
            title = title if title else mw.get_title()
            self.on_done(title)

    def on_done(self, title):
        if title:
            title = mw.pagename_clear(title)

        self.title = title
        panel_passwd = mw.InputPanelPassword()
        panel_passwd.command_run = self.command_run
        panel_passwd.get_password()

    def command_run(self, password):
        # cases:
        # from view with page, opened from other site_active than in global settings - new page will be from the same site
        # from view with page, open page with another lang site - site param must be defined, will set it
        # from view with undefined site (new) open page by global site_active setting
        if not self.site_active:
            self.site_active = mw.get_view_site()

        if self.action == 'mediawiker_show_page' and mw.get_setting('mediawiker_newtab_ongetpage', False):
            self.run_in_new_window = True
        elif self.action == 'mediawiker_reopen_page':
            self.action = 'mediawiker_show_page'
            self.run_in_new_window = self.kwargs.get('new_tab', False)

        if self.run_in_new_window:
            self.window.new_file()
            self.run_in_new_window = False

        self.window.active_view().settings().set('mediawiker_site', self.site_active)

        args = {"title": self.title, "password": password}
        if self.action_params:
            for key in self.action_params.keys():
                args[key] = self.action_params[key]
        self.window.active_view().run_command(self.action, args)
        try:
            self.get_notifications(password)
        except Exception as e:
            print('Mediawiker exception: %s' % e)

    def get_notifications(self, password):
        # check notifications on page open command
        if self.action == 'mediawiker_show_page' and self.check_notifications:
            sitecon = mw.get_connect(password)
            ns = sitecon.notifications()
            is_notify_exists = False
            if ns:
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
            if is_notify_exists:
                show_notify = sublime.ok_cancel_dialog('You have new notifications.')
                if show_notify:
                    self.window.run_command("mediawiker_get_notifications", {"title": None, "password": password})
