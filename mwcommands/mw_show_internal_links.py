#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import webbrowser

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerShowInternalLinksCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    actions = ['Goto internal link', 'Open page in editor', 'Open page in browser']
    selected = None

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = mw.get_internal_links_regions(self.view)
        self.items = [x[0] for x in self.regions]
        if self.items:
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_select), 1)
        else:
            sublime.status_message('No internal links was found.')

    def on_select(self, index):
        if index >= 0:
            self.selected = index
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.actions, self.on_done), 1)

    def on_done(self, index):
        if index == 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[self.selected][1])
            self.view.sel().clear()
            self.view.sel().add(self.regions[self.selected][1])
        elif index == 1:
            sublime.set_timeout(lambda: self.view.window().run_command("mediawiker_page", {"action": "mediawiker_show_page", "title": self.items[self.selected]}), 1)
        elif index == 2:
            url = mw.get_page_url(self.items[self.selected])
            webbrowser.open(url)
