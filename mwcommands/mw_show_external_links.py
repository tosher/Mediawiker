#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import webbrowser
import sublime
import sublime_plugin
from . import mw_utils as utils
from . import mw_parser as par


class MediawikerShowExternalLinksCommand(sublime_plugin.TextCommand):
    actions = ['Goto external link', 'Open link in browser']

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.view, 'is_here')

    def run(self, edit):
        self.item = None
        page = utils.api.get_page(utils.get_title())
        linksgen = utils.api.get_page_extlinks(page)

        self.p = par.Parser(self.view)
        self.p.register_all(par.Comment, par.Pre, par.Source, par.Nowiki, par.Link, par.ExternalLink)
        if not self.p.parse():
            return

        self.items_menu = [self.link_for_menu(l) for l in linksgen]
        self.items_find = [l.split('#')[0] for l in linksgen]
        self.items_open = [l for l in linksgen]

        if self.items_menu:
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items_menu, self.on_select), 1)
        else:
            utils.status_message('No external links was found.')

    def link_for_menu(self, link):
        return utils.strunquote(link.split('#')[0])

    def on_select(self, index):
        if index >= 0:
            self.item = {
                'find': self.items_find[index],
                'open': self.items_open[index]
            }
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.actions, self.on_done), 1)

    def find_item(self):
        last_found_position = self.view.sel()[-1].b + 1
        for l in self.p.externallinks:
            if l.url == self.item['find'] and l.region.a > last_found_position:
                return l.region

        for l in self.p.externallinks:
            if l.url == self.item['find']:
                return l.region

    def select_item(self):
        if self.item is not None:
            r = self.find_item()
            if r:
                self.view.sel().clear()
                self.view.sel().add(sublime.Region(r.a, r.a))
                self.view.show(r)

    def on_done(self, index):
        if self.item is not None:
            if index == 0:
                self.select_item()
            elif index == 1:
                self.browse_item()

    def browse_item(self):
        if self.item is not None:
            webbrowser.open(self.item['open'])
