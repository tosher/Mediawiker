#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerShowTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'^(={1,5})\s?(.*?)\s?={1,5}$'

    def is_visible(self, *args):
        return utils.props.get_view_setting(self.view, 'is_here')

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        # self.items = map(self.get_header, self.regions)
        self.items = [self.get_header(x) for x in self.regions]
        sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_done), 1)

    def get_header(self, region):
        TAB = ' ' * 4
        h = self.view.substr(region).rstrip('=')
        h_as_list = list(h)
        for i, char in enumerate(h_as_list):
            if char == '=':
                h_as_list[i] = TAB
            else:
                break
        return ''.join(h_as_list)

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[index])
            self.view.sel().clear()
            self.view.sel().add(self.regions[index])
