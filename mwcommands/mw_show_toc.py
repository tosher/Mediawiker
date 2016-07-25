#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

# import sys
import re

import sublime
import sublime_plugin

# pythonver = sys.version_info[0]
# if pythonver >= 3:
#     from . import mw_utils as mw
# else:
#     import mw_utils as mw


class MediawikerShowTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'^(={1,5})\s?(.*?)\s?={1,5}'

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        # self.items = map(self.get_header, self.regions)
        self.items = [self.get_header(x) for x in self.regions]
        sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_done), 1)

    def get_header(self, region):
        TAB_SIZE = ' ' * 4
        return re.sub(self.pattern, r'\1\2', self.view.substr(region)).replace('=', TAB_SIZE)[len(TAB_SIZE):]

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[index])
            self.view.sel().clear()
            self.view.sel().add(self.regions[index])
