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
    SITE_ON = '> '
    SITE_OFF = ' ' * 4
    site_active = ''

    def run(self):
        self.site_active = mw.get_view_site()
        sites = mw.get_setting('site')
        self.site_keys = [self.is_checked(x) for x in sorted(sites.keys(), key=str.lower)]
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.site_keys, self.on_done), 1)

    def is_checked(self, site_key):
        checked = self.SITE_ON if site_key == self.site_active else self.SITE_OFF
        return '%s%s' % (checked, site_key)

    def on_done(self, index):
        # not escaped
        if index >= 0:
            site_active = self.site_keys[index].strip()
            if site_active.startswith(self.SITE_ON):
                site_active = site_active[len(self.SITE_ON):]
            # force to set site_active in global and in view settings
            if mw.props.get_view_setting(self.window.active_view(), 'is_here'):
                mw.props.set_view_setting(self.window.active_view(), 'site', site_active)
            mw.set_setting("site_active", site_active)
