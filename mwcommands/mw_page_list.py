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


class MediawikerPageListCommand(sublime_plugin.WindowCommand):

    def run(self, storage_name='mediawiker_pagelist'):
        # site_name_active = mw.get_setting('mediawiki_site_active')
        site_name_active = mw.get_view_site()
        mediawiker_pagelist = mw.get_setting(storage_name, {})
        self.my_pages = mediawiker_pagelist.get(site_name_active, [])
        if self.my_pages:
            self.my_pages.reverse()
            # error 'Quick panel unavailable' fix with timeout..
            sublime.set_timeout(lambda: self.window.show_quick_panel(self.my_pages, self.on_done), 1)
        else:
            sublime.status_message('List of pages for wiki "%s" is empty.' % (site_name_active))

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            title = self.my_pages[index]
            try:
                self.window.run_command("mediawiker_page", {"title": title, "action": "mediawiker_show_page"})
            except ValueError as e:
                sublime.message_dialog(e)
