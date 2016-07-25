#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

# import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerFavoritesAddCommand(sublime_plugin.WindowCommand):

    def run(self):
        title = mw.get_title()
        mw.save_mypages(title=title, storage_name='mediawiker_favorites')


class MediawikerFavoritesOpenCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.run_command("mediawiker_page_list", {"storage_name": 'mediawiker_favorites'})
