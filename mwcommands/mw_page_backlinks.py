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


class MediawikerShowPageBacklinksCommand(sublime_plugin.WindowCommand):
    ''' alias to PageBacklinks command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_page_backlinks"})


class MediawikerPageBacklinksCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        title = mw.get_title()
        self.mw_get_page_backlinks(title)

        if self.links:
            sublime.active_window().show_quick_panel(self.links, self.on_done)
        else:
            mw.status_message('Unable to find links to this page')

    def mw_get_page_backlinks(self, title):
        self.links = []
        links_limit = mw.get_setting('mediawiki_linkstopage_limit', 5)
        page = mw.api.get_page(title)

        # backlinks to page
        linksgen = mw.api.get_page_backlinks(page, links_limit)
        if linksgen:
            while True:
                try:
                    prop = linksgen.next()
                    self.links.append(mw.api.page_attr(prop, 'name'))
                except StopIteration:
                    break

        # pages, transcludes this
        linksgen = mw.api.get_page_embeddedin(page, links_limit)
        if linksgen:
            while True:
                try:
                    prop = linksgen.next()
                    self.links.append(mw.api.page_attr(prop, 'name'))
                except StopIteration:
                    break

    def on_done(self, index):
        if index >= 0:
            self.page_name = self.links[index]

            sublime.active_window().run_command('mediawiker_page', {'action': 'mediawiker_show_page', 'action_params': {'title': self.page_name}})
