#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerSetActiveSiteCommand(sublime_plugin.WindowCommand):
    site_keys = []
    SITE_ON = '> '
    SITE_OFF = ' ' * 4
    TAB = ' ' * 6
    site_active = ''

    def run(self):
        self.site_active = utils.get_view_site()
        sites = utils.props.get_setting('site')

        self.sites_list = []
        self.sites_names = []
        for k in sorted(sites.keys()):
            auth_src = ''
            auth_type = utils.props.get_site_setting(k, 'authorization_type')
            if auth_type == 'login':
                auth_src = utils.props.get_site_setting(k, 'username')
            elif auth_type == 'cookies':
                auth_src = utils.props.get_site_setting(k, 'cookies_browser')

            rec = [
                '{activated} {name}'.format(
                    activated=self.SITE_ON if self.activated(k) else self.SITE_OFF,
                    name=k
                ),
                '{tab}Auth type: {auth_type}{auth_src}'.format(
                    tab=self.TAB,
                    auth_type=auth_type,
                    auth_src=' ({})'.format(auth_src) if auth_src else ''
                )
            ]
            self.sites_list.append(rec)
            self.sites_names.append(k)
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.sites_list, self.on_done), 1)

    def activated(self, site_name):
        if site_name == self.site_active:
            return True
        return False

    def on_done(self, index):
        if index >= 0:
            site_active = self.sites_names[index]
            # force to set site_active in global and in view settings
            if utils.props.get_view_setting(self.window.active_view(), 'is_here'):
                utils.props.set_view_setting(self.window.active_view(), 'site', site_active)
            utils.props.set_setting("site_active", site_active)
