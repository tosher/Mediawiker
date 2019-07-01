#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerAddChildSiteCommand(sublime_plugin.WindowCommand):
    TAB = ' ' * 6

    def run(self):
        self.site_parent = None
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
                '{}'.format(k),
                '{tab}Auth type: {auth_type}{auth_src}'.format(
                    tab=self.TAB,
                    auth_type=auth_type,
                    auth_src=' (%s)' % auth_src if auth_src else ''
                )
            ]
            self.sites_list.append(rec)
            self.sites_names.append(k)
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.sites_list, self.on_done_parent), 1)

    def on_done_parent(self, index):
        if index >= 0:
            self.site_parent = self.sites_names[index]

        self.window.show_input_panel('Site host:', '', self.on_done, None, None)

    def on_done(self, host):
        sites = utils.props.get_setting('site')
        if host not in sites:
            sites[host] = {}
            utils.props.set_setting('site', sites)
        utils.props.set_site_setting(host, 'host', host)
        utils.props.set_site_setting(host, 'parent', self.site_parent)
