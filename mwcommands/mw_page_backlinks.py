#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerShowPageBacklinksCommand(sublime_plugin.WindowCommand):
    ''' alias to PageBacklinks command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('page_backlinks')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerPageBacklinksCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        title = utils.get_title()
        self.mw_get_page_backlinks(title)

        if self.links:
            sublime.active_window().show_quick_panel(self.links, self.on_done)
        else:
            utils.status_message('Unable to find links to this page')

    def mw_get_page_backlinks(self, title):
        self.links = []
        links_limit = utils.props.get_setting('linkstopage_limit')
        page = utils.api.get_page(title)

        # backlinks to page
        linksgen = utils.api.get_page_backlinks(page, links_limit)
        if linksgen:
            while True:
                try:
                    prop = linksgen.next()
                    self.links.append(utils.api.page_attr(prop, 'name'))
                except StopIteration:
                    break

        # pages, transcludes this
        linksgen = utils.api.get_page_embeddedin(page, links_limit)
        if linksgen:
            while True:
                try:
                    prop = linksgen.next()
                    self.links.append(utils.api.page_attr(prop, 'name'))
                except StopIteration:
                    break

    def on_done(self, index):
        if index >= 0:
            self.page_name = self.links[index]

            sublime.active_window().run_command(utils.cmd('page'), {'action': utils.cmd('show_page'), 'action_params': {'title': self.page_name}})
