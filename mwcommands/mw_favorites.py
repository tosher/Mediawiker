#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

# import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as utils
else:
    import mw_utils as utils


class MediawikerFavoritesAddCommand(sublime_plugin.WindowCommand):

    def run(self):
        title = utils.get_title()
        utils.save_mypages(title=title, storage_name='favorites')


class MediawikerFavoritesOpenCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.run_command(utils.cmd('page_list'), {'storage_name': 'favorites'})
