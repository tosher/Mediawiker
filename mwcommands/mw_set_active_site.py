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


class MediawikerSetActiveSiteCommand(sublime_plugin.WindowCommand):
    site_keys = []
    site_on = '> '
    site_off = ' ' * 4
    site_active = ''

    def run(self):
        # self.site_active = mw.get_setting('mediawiki_site_active')
        self.site_active = mw.get_view_site()
        sites = mw.get_setting('mediawiki_site')
        # self.site_keys = map(self.is_checked, list(sites.keys()))
        self.site_keys = [self.is_checked(x) for x in sites.keys()]
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.site_keys, self.on_done), 1)

    def is_checked(self, site_key):
        checked = self.site_on if site_key == self.site_active else self.site_off
        return '%s%s' % (checked, site_key)

    def on_done(self, index):
        # not escaped
        if index >= 0:
            site_active = self.site_keys[index].strip()
            if site_active.startswith(self.site_on):
                site_active = site_active[len(self.site_on):]
            # force to set site_active in global and in view settings
            # current_syntax = self.window.active_view().settings().get('syntax')
            # if current_syntax is not None and current_syntax.endswith('Mediawiker/Mediawiki.tmLanguage'):
            if self.window.active_view().settings().get('mediawiker_is_here', False):
                self.window.active_view().settings().set('mediawiker_site', site_active)
            mw.set_setting("mediawiki_site_active", site_active)
