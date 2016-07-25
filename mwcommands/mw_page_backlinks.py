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

    def run(self, edit, title, password):
        sitecon = mw.get_connect(password)
        self.mw_get_page_backlinks(sitecon, title)

        if self.links:
            sublime.active_window().show_quick_panel(self.links, self.on_done)
        else:
            sublime.status_message('Unable to find links to this page')

    def mw_get_page_backlinks(self, site, title):
        self.links = []
        links_limit = mw.get_setting('mediawiki_linkstopage_limit', 5)
        page = site.Pages[title]

        # backlinks to page
        linksgen = page.backlinks(limit=links_limit)
        if linksgen:
            while True:
                try:
                    prop = linksgen.next()
                    self.links.append(prop.name)
                except StopIteration:
                    break

        # pages, transcludes this
        linksgen = page.embeddedin(limit=links_limit)
        if linksgen:
            while True:
                try:
                    prop = linksgen.next()
                    self.links.append(prop.name)
                except StopIteration:
                    break

    def on_done(self, index):
        if index >= 0:
            self.page_name = self.links[index]

            sublime.active_window().run_command("mediawiker_page", {"title": self.page_name, "action": "mediawiker_show_page"})
