#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import re
import webbrowser

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerShowExternalLinksCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'[^\[]\[{1}(\w.*?)(\s.*?)?\]{1}[^\]]'
    actions = ['Goto external link', 'Open link in browser']
    selected = None

    def run(self, edit):
        # TODO: use API..
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        self.items = [self.get_header(x) for x in self.regions]
        self.urls = [self.get_url(x) for x in self.regions]
        if self.items:
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_select), 1)
        else:
            sublime.status_message('No external links was found.')

    def prepare_header(self, header):
        maxlen = 70
        link_url = mw.strunquote(header.group(1))
        link_descr = ''
        if header.group(2) is not None:
            link_descr = re.sub(r'<.*?>', '', header.group(2))
        postfix = '..' if len(link_descr) > maxlen else ''
        return '%s: %s%s' % (link_url, link_descr[:maxlen], postfix)

    def get_header(self, region):
        # return re.sub(self.pattern, r'\1: \2', self.view.substr(region))
        return re.sub(self.pattern, self.prepare_header, self.view.substr(region))

    def get_url(self, region):
        return re.sub(self.pattern, r'\1', self.view.substr(region))

    def on_select(self, index):
        if index >= 0:
            self.selected = index
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.actions, self.on_done), 1)

    def on_done(self, index):
        if index == 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[self.selected])
            self.view.sel().clear()
            self.view.sel().add(self.regions[self.selected])
        elif index == 1:
            webbrowser.open(self.urls[self.selected])
